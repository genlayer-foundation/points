import csv
import datetime
import io
import posixpath
import re
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree

from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.text import slugify

from poaps.models import PoapClaim, PoapDrop, PoapImportBatch
from poaps.services import find_user_for_legacy_claim


@dataclass
class ArchiveDrop:
    legacy_id: str
    event_date: str
    title: str
    data_path: str
    image_path: str


class Command(BaseCommand):
    help = 'Import a full POAP archive zip with collector exports and mandatory badge images.'

    DATA_FILENAME_RE = re.compile(
        r'^POAP_drop_(?P<legacy_id>\d+)_collectors_'
        r'(?P<date>\d{4}-\d{2}-\d{2})(?P<title>.*?)\.(?P<ext>csv|xlsx)$',
        re.IGNORECASE,
    )
    IMAGE_FILENAME_RE = re.compile(
        r'^\s*ID\s*(?P<legacy_id>\d+)(?P<title>.*?)$',
        re.IGNORECASE,
    )
    WALLET_FIELDS = [
        'ethereum_address',
        'ethereum address',
        'wallet',
        'wallet_address',
        'wallet address',
        'collector_address',
        'collector address',
        'address',
    ]
    EMAIL_FIELDS = [
        'email_address',
        'email address',
        'collector_email',
        'collector email',
        'email',
    ]
    ENS_FIELDS = ['ens', 'ens_name', 'ens name']
    EXTERNAL_ID_FIELDS = [
        'token_id',
        'token id',
        'mint_id',
        'mint id',
        'external_id',
        'external id',
    ]

    def add_arguments(self, parser):
        parser.add_argument('archive_path')
        parser.add_argument('--source', default='poap_archive')
        parser.add_argument('--description', default='')
        parser.add_argument(
            '--status',
            default=PoapDrop.STATUS_ARCHIVED,
            choices=[
                PoapDrop.STATUS_DRAFT,
                PoapDrop.STATUS_ACTIVE,
                PoapDrop.STATUS_ARCHIVED,
            ],
        )
        parser.add_argument(
            '--upload-artwork',
            action='store_true',
            help='Upload every matched image to Cloudinary and store the returned URL/public id.',
        )
        parser.add_argument(
            '--cloudinary-folder',
            default='tally/poaps',
            help='Cloudinary folder used with --upload-artwork.',
        )
        parser.add_argument(
            '--no-max-claims-from-rows',
            action='store_false',
            dest='max_claims_from_rows',
            help='Do not set PoapDrop.max_claims from the number of rows in each legacy export.',
        )
        parser.set_defaults(max_claims_from_rows=True)
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Validate archive structure and report what would be imported without writing the database.',
        )

    def handle(self, *args, **options):
        archive_path = Path(options['archive_path'])
        if not archive_path.exists():
            raise CommandError(f'Archive does not exist: {archive_path}')

        if not options['dry_run'] and not options['upload_artwork']:
            raise CommandError(
                'Images are mandatory. Pass --upload-artwork to upload badge images to Cloudinary.'
            )

        try:
            archive = zipfile.ZipFile(archive_path)
        except zipfile.BadZipFile as exc:
            raise CommandError(f'Invalid zip archive: {archive_path}') from exc

        with archive:
            drops, duplicate_data_paths, image_only_ids = self._collect_drops(archive)
            missing_images = [drop for drop in drops if not drop.image_path]

            self.stdout.write(f'Found {len(drops)} distinct POAP drops.')
            if duplicate_data_paths:
                self.stdout.write(self.style.WARNING(
                    f'Skipping {len(duplicate_data_paths)} duplicate data file(s): '
                    f'{", ".join(duplicate_data_paths[:5])}'
                ))
            if image_only_ids:
                self.stdout.write(self.style.WARNING(
                    f'Found {len(image_only_ids)} image(s) without a matching collector export.'
                ))

            if missing_images:
                missing = ', '.join(f'{drop.legacy_id} ({drop.data_path})' for drop in missing_images[:10])
                raise CommandError(
                    f'Every POAP export must have an image. Missing {len(missing_images)} image(s): {missing}'
                )

            if options['dry_run']:
                total_rows = sum(len(self._read_rows(archive, drop.data_path)) for drop in drops)
                self.stdout.write(self.style.SUCCESS(
                    f'Dry run passed: {len(drops)} drops, {total_rows} collector row(s), '
                    'all selected drops have images.'
                ))
                return

            batch = PoapImportBatch.objects.create(
                source_name=options['source'],
                file_name=str(archive_path),
            )
            errors = []

            for drop_entry in drops:
                try:
                    existing_drop = self._existing_drop_for_legacy_id(drop_entry.legacy_id)
                    rows = self._read_rows(archive, drop_entry.data_path)
                    artwork = self._prepare_artwork(archive, drop_entry, options, existing_drop=existing_drop)
                    drop = self._upsert_drop(
                        drop_entry,
                        artwork,
                        options,
                        row_count=len(rows),
                        existing_drop=existing_drop,
                    )
                except Exception as exc:
                    batch.error_count += 1
                    errors.append({'drop': drop_entry.data_path, 'error': str(exc)})
                    continue

                for row_number, row in enumerate(rows, start=2):
                    batch.total_rows += 1
                    try:
                        self._import_claim_row(batch, drop, drop_entry, row)
                    except Exception as exc:
                        batch.error_count += 1
                        errors.append({
                            'drop': drop_entry.data_path,
                            'row': row_number,
                            'error': str(exc),
                            'data': row,
                        })

            batch.errors = errors
            batch.save()

        self.stdout.write(self.style.SUCCESS(
            f'Imported {batch.imported_count}/{batch.total_rows} claims across {len(drops)} POAPs '
            f'({batch.matched_count} wallet matched, {batch.unmatched_count} unmatched, '
            f'{batch.error_count} errors).'
        ))

    def _collect_drops(self, archive):
        data_by_id = {}
        duplicate_data_paths = []
        image_by_id = {}

        for name in archive.namelist():
            if self._is_directory_or_system_file(name):
                continue

            data_meta = self._data_metadata(name)
            if data_meta:
                legacy_id = data_meta['legacy_id']
                current = data_by_id.get(legacy_id)
                if current and self._data_priority(current['path']) <= self._data_priority(name):
                    duplicate_data_paths.append(name)
                    continue
                if current:
                    duplicate_data_paths.append(current['path'])
                data_by_id[legacy_id] = data_meta
                continue

            image_meta = self._image_metadata(name)
            if image_meta:
                image_by_id.setdefault(image_meta['legacy_id'], name)

        drops = []
        for legacy_id, data_meta in sorted(
            data_by_id.items(),
            key=lambda item: (item[1]['event_date'], int(item[0])),
            reverse=True,
        ):
            image_path = image_by_id.get(legacy_id, '')
            title = data_meta['title'] or self._title_from_image_path(image_path) or f'Legacy POAP {legacy_id}'
            drops.append(ArchiveDrop(
                legacy_id=legacy_id,
                event_date=data_meta['event_date'],
                title=title,
                data_path=data_meta['path'],
                image_path=image_path,
            ))

        image_only_ids = sorted(set(image_by_id) - set(data_by_id), key=int)
        return drops, duplicate_data_paths, image_only_ids

    def _import_claim_row(self, batch, drop, drop_entry, row):
        wallet = self._row_value(row, self.WALLET_FIELDS)
        email = self._row_value(row, self.EMAIL_FIELDS)
        ens = self._row_value(row, self.ENS_FIELDS)
        external_id = self._row_value(row, self.EXTERNAL_ID_FIELDS)
        user = find_user_for_legacy_claim(wallet=wallet)

        if user:
            if PoapClaim.objects.filter(drop=drop, user=user).exists():
                batch.imported_count += 1
                return

            unmatched_claim = self._unmatched_claim_for_wallet(drop, wallet)
            if unmatched_claim:
                metadata = dict(unmatched_claim.legacy_metadata or {})
                metadata.update(row)
                if ens:
                    metadata['ens'] = ens
                metadata['legacy_poap_id'] = drop_entry.legacy_id
                unmatched_claim.user = user
                unmatched_claim.legacy_email = email or unmatched_claim.legacy_email
                unmatched_claim.legacy_external_id = external_id or unmatched_claim.legacy_external_id
                unmatched_claim.legacy_metadata = metadata
                unmatched_claim.import_batch = batch
                unmatched_claim.save(update_fields=[
                    'user',
                    'legacy_email',
                    'legacy_external_id',
                    'legacy_metadata',
                    'import_batch',
                    'updated_at',
                ])
                batch.imported_count += 1
                batch.matched_count += 1
                return

        if not user and self._unmatched_claim_exists(drop, wallet, email, external_id):
            batch.imported_count += 1
            batch.unmatched_count += 1
            return

        metadata = dict(row)
        if ens:
            metadata['ens'] = ens
        metadata['legacy_poap_id'] = drop_entry.legacy_id

        try:
            with transaction.atomic():
                PoapClaim.objects.create(
                    drop=drop,
                    user=user,
                    claim_method=PoapClaim.CLAIM_LEGACY,
                    source=PoapClaim.SOURCE_LEGACY_IMPORT,
                    claimed_at=drop.event_start_at,
                    legacy_wallet_address=wallet,
                    legacy_email=email,
                    legacy_external_id=external_id,
                    legacy_metadata=metadata,
                    import_batch=batch,
                )
            batch.imported_count += 1
            if user:
                batch.matched_count += 1
            else:
                batch.unmatched_count += 1
        except IntegrityError:
            batch.imported_count += 1

    def _upsert_drop(self, drop_entry, artwork, options, row_count, existing_drop=None):
        slug = self._default_slug(drop_entry.title, drop_entry.legacy_id)
        defaults = {
            'title': drop_entry.title,
            'description': options['description'],
            'artwork_url': artwork['artwork_url'],
            'artwork_public_id': artwork['artwork_public_id'],
            'event_start_at': self._parse_date(drop_entry.event_date),
            'event_end_at': None,
            'status': options['status'],
            'legacy_poap_id': drop_entry.legacy_id,
            'max_claims': row_count if options['max_claims_from_rows'] else None,
        }

        if existing_drop:
            drop = existing_drop
            for field, value in defaults.items():
                setattr(drop, field, value)
            if not drop.slug:
                drop.slug = slug
            drop.save()
            return drop

        drop, _ = PoapDrop.objects.update_or_create(
            slug=slug,
            defaults=defaults,
        )
        return drop

    def _prepare_artwork(self, archive, drop_entry, options, existing_drop=None):
        if existing_drop and existing_drop.artwork_url and existing_drop.artwork_public_id:
            return {
                'artwork_url': existing_drop.artwork_url,
                'artwork_public_id': existing_drop.artwork_public_id,
            }

        image_data = archive.read(drop_entry.image_path)
        suffix = PurePosixPath(drop_entry.image_path).suffix.lower() or '.webp'
        filename = f'poap-{drop_entry.legacy_id}{suffix}'

        return self._upload_artwork(
            image_data,
            filename=filename,
            drop_entry=drop_entry,
            folder=options['cloudinary_folder'],
        )

    def _upload_artwork(self, image_data, *, filename, drop_entry, folder):
        try:
            from users.cloudinary_service import CloudinaryService

            image_file = io.BytesIO(image_data)
            image_file.name = filename
            public_id = f'poap_{drop_entry.legacy_id}_{int(time.time() * 1000)}'
            result = CloudinaryService.upload_image(
                image_file,
                folder=folder,
                public_id=public_id,
            )
        except Exception as exc:
            raise CommandError(f'Artwork upload failed for POAP {drop_entry.legacy_id}: {exc}') from exc

        return {
            'artwork_url': result.get('url', ''),
            'artwork_public_id': result.get('public_id', ''),
        }

    def _existing_drop_for_legacy_id(self, legacy_id):
        existing = list(PoapDrop.objects.filter(legacy_poap_id=legacy_id)[:2])
        if len(existing) > 1:
            raise CommandError(
                f'Multiple existing POAP drops use legacy POAP ID {legacy_id}. '
                'Fix the duplicates before running the import.'
            )
        return existing[0] if existing else None

    def _read_rows(self, archive, path):
        data = archive.read(path)
        if path.lower().endswith('.xlsx'):
            return self._read_xlsx_rows(data)
        return self._read_csv_rows(data)

    def _read_csv_rows(self, data):
        stream = io.TextIOWrapper(io.BytesIO(data), encoding='utf-8-sig', newline='')
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            return []
        return [self._clean_row(row) for row in reader]

    def _read_xlsx_rows(self, data):
        matrix = self._read_xlsx_matrix(data)
        if not matrix:
            return []

        headers = [str(value or '').strip() for value in matrix[0]]
        rows = []
        for values in matrix[1:]:
            if not any(str(value or '').strip() for value in values):
                continue
            row = {}
            for index, header in enumerate(headers):
                if header:
                    row[header] = values[index] if index < len(values) else ''
            rows.append(self._clean_row(row))
        return rows

    def _read_xlsx_matrix(self, data):
        main_ns = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
        rel_ns = '{http://schemas.openxmlformats.org/package/2006/relationships}'
        office_rel_ns = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'

        with zipfile.ZipFile(io.BytesIO(data)) as workbook:
            shared_strings = self._xlsx_shared_strings(workbook, main_ns)
            workbook_root = ElementTree.fromstring(workbook.read('xl/workbook.xml'))
            sheets = workbook_root.findall(f'{main_ns}sheets/{main_ns}sheet')
            if not sheets:
                return []

            rel_id = sheets[0].attrib.get(f'{office_rel_ns}id')
            rels_root = ElementTree.fromstring(workbook.read('xl/_rels/workbook.xml.rels'))
            sheet_target = ''
            for rel in rels_root.findall(f'{rel_ns}Relationship'):
                if rel.attrib.get('Id') == rel_id:
                    sheet_target = rel.attrib.get('Target', '')
                    break
            if not sheet_target:
                return []

            sheet_path = self._xlsx_target_path(sheet_target)
            sheet_root = ElementTree.fromstring(workbook.read(sheet_path))
            rows = []
            for row in sheet_root.findall(f'.//{main_ns}sheetData/{main_ns}row'):
                values = []
                for cell in row.findall(f'{main_ns}c'):
                    ref = cell.attrib.get('r', '')
                    column_index = self._xlsx_column_index(ref)
                    while len(values) < column_index:
                        values.append('')
                    values.append(self._xlsx_cell_value(cell, shared_strings, main_ns))
                rows.append(values)
            return rows

    def _xlsx_shared_strings(self, workbook, main_ns):
        if 'xl/sharedStrings.xml' not in workbook.namelist():
            return []
        root = ElementTree.fromstring(workbook.read('xl/sharedStrings.xml'))
        return [
            ''.join(text_node.text or '' for text_node in item.iter(f'{main_ns}t'))
            for item in root.findall(f'{main_ns}si')
        ]

    def _xlsx_cell_value(self, cell, shared_strings, main_ns):
        cell_type = cell.attrib.get('t')
        if cell_type == 'inlineStr':
            return ''.join(text_node.text or '' for text_node in cell.iter(f'{main_ns}t')).strip()

        value_node = cell.find(f'{main_ns}v')
        if value_node is None:
            return ''

        raw = value_node.text or ''
        if cell_type == 's':
            try:
                return shared_strings[int(raw)].strip()
            except (IndexError, ValueError):
                return ''
        return raw.strip()

    def _xlsx_target_path(self, target):
        if target.startswith('/'):
            return target.lstrip('/')
        return posixpath.normpath(posixpath.join('xl', target))

    def _xlsx_column_index(self, cell_reference):
        match = re.match(r'([A-Z]+)', (cell_reference or '').upper())
        if not match:
            return 0
        value = 0
        for char in match.group(1):
            value = value * 26 + ord(char) - ord('A') + 1
        return value - 1

    def _data_metadata(self, path):
        filename = PurePosixPath(path).name
        match = self.DATA_FILENAME_RE.match(filename)
        if not match:
            return None

        return {
            'path': path,
            'legacy_id': match.group('legacy_id'),
            'event_date': match.group('date'),
            'title': self._clean_title(match.group('title')),
        }

    def _image_metadata(self, path):
        suffix = PurePosixPath(path).suffix.lower()
        if suffix not in {'.png', '.jpg', '.jpeg', '.webp'}:
            return None

        stem = PurePosixPath(path).stem.strip()
        match = self.IMAGE_FILENAME_RE.search(stem)
        if not match:
            return None
        return {
            'legacy_id': match.group('legacy_id'),
            'title': self._clean_title(match.group('title')),
        }

    def _title_from_image_path(self, path):
        if not path:
            return ''
        meta = self._image_metadata(path)
        return meta['title'] if meta else ''

    def _data_priority(self, path):
        return 0 if path.lower().endswith('.csv') else 1

    def _is_directory_or_system_file(self, path):
        name = PurePosixPath(path).name
        return path.endswith('/') or name.startswith('.') or name == '__MACOSX'

    def _clean_title(self, value):
        value = (value or '').strip()
        value = re.sub(r'^\s*-\s*', '', value)
        value = value.replace('_', ' ')
        value = re.sub(r'\s+', ' ', value)
        return value.strip()

    def _clean_row(self, row):
        return {
            (key or '').strip(): '' if value is None else str(value).strip()
            for key, value in row.items()
            if key is not None
        }

    def _row_value(self, row, candidates):
        normalized_row = {
            self._normalize_header(key): value
            for key, value in row.items()
        }
        for candidate in candidates:
            value = (normalized_row.get(self._normalize_header(candidate)) or '').strip()
            if value:
                return value
        return ''

    def _normalize_header(self, value):
        return re.sub(r'[^a-z0-9]', '', (value or '').lower())

    def _unmatched_claim_exists(self, drop, wallet, email, external_id):
        queryset = PoapClaim.objects.filter(drop=drop, user__isnull=True)
        if wallet:
            return queryset.filter(legacy_wallet_address__iexact=wallet).exists()
        if external_id:
            return queryset.filter(legacy_external_id=external_id).exists()
        if email:
            return queryset.filter(legacy_email__iexact=email).exists()
        return False

    def _unmatched_claim_for_wallet(self, drop, wallet):
        if not wallet:
            return None
        return (
            PoapClaim.objects
            .filter(drop=drop, user__isnull=True, legacy_wallet_address__iexact=wallet)
            .order_by('created_at')
            .first()
        )

    def _default_slug(self, title, legacy_poap_id):
        base = slugify(title)[:150] or 'legacy-poap'
        if legacy_poap_id:
            return f'{base}-{legacy_poap_id}'
        return base

    def _parse_date(self, value):
        parsed = datetime.datetime.fromisoformat(value)
        if timezone.is_naive(parsed):
            parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
        return parsed
