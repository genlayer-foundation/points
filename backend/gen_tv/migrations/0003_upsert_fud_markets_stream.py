from datetime import datetime, timedelta, timezone

from django.db import migrations


FUD_STREAM = {
    "slug": "fud-markets-testnet-launch",
    "title": "FUD Markets Testnet Launch Livestream",
    "description": (
        "@raskovsky and @theboymarc0x's deep dive on the recently launched app FUD "
        "Markets that uses GenLayer's technology, their Testnet and Mainnet phases.\n\n"
        "Speakers: @raskovsky, @theboymarc0x"
    ),
    "url": "https://x.com/GenLayer/status/2054659264912687394",
    "image_url": "https://res.cloudinary.com/dfqmoeawa/image/upload/gen_tv/fud-markets-testnet-launch.png",
    "starts_at": datetime(2026, 5, 15, 15, 0, tzinfo=timezone.utc),
    "category": "internal",
    "is_active": True,
}


def upsert_fud_markets_stream(apps, schema_editor):
    Stream = apps.get_model("gen_tv", "Stream")
    starts_at = FUD_STREAM["starts_at"]
    defaults = {
        key: value
        for key, value in FUD_STREAM.items()
        if key != "slug"
    }
    defaults["ends_at"] = starts_at + timedelta(minutes=30)

    stream = Stream.objects.filter(url=FUD_STREAM["url"]).order_by("id").first()
    if stream is None:
        stream = Stream.objects.filter(slug=FUD_STREAM["slug"]).first()

    if stream is None:
        Stream.objects.create(slug=FUD_STREAM["slug"], **defaults)
        return

    for field, value in defaults.items():
        setattr(stream, field, value)
    stream.save(update_fields=[*defaults.keys(), "updated_at"])


class Migration(migrations.Migration):

    dependencies = [
        ("gen_tv", "0002_seed_streams"),
    ]

    operations = [
        migrations.RunPython(upsert_fud_markets_stream, migrations.RunPython.noop),
    ]
