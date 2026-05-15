from datetime import datetime, timedelta, timezone

from django.db import migrations
from django.utils.text import slugify


CLOUDINARY_BASE = "https://res.cloudinary.com/dfqmoeawa/image/upload/gen_tv"
DEFAULT_BANNER = f"{CLOUDINARY_BASE}/default-banner.png"
DURATION = timedelta(minutes=30)


def _at(year: int, month: int, day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


# Each tuple: (slug, title, starts_at, source_url, description, has_own_banner)
# `has_own_banner=True` -> uses gen_tv/<slug>.png; False -> default banner.
STREAMS: list[tuple[str, str, datetime, str, str, bool]] = [
    (
        "barcelona-openclaw-meetup",
        "Barcelona Openclaw Meetup Livestream",
        _at(2026, 2, 10, 18, 0),
        "https://x.com/i/broadcasts/1mnxeNgXbbqKX",
        "Discussion of the emerging OpenClaw technology.\n\n"
        "Speakers: @MorpheusAIs's speaker, @driudor, @akka_io_'s speaker, "
        "@joaquinbressan, @cognocracy, @kstellana",
        False,
    ),
    (
        "presenting-hackathon",
        "Presenting Hackathon",
        _at(2026, 3, 17, 16, 0),
        "https://x.com/i/broadcasts/1NGaraDelYdJj",
        "Ivan introduced the Hackathon, outlining its timeline, main features, "
        "award categories, and focus areas.\n\n"
        "Speakers: @raskovsky",
        True,
    ),
    (
        "from-zero-to-genlayer",
        "From Zero to GenLayer",
        _at(2026, 3, 19, 11, 0),
        "https://x.com/i/broadcasts/1jxXgeaLLgRJZ",
        "A vibecoding session organized specifically for the Hackathon. The session "
        "covered the main aspects of development on GenLayer, including consensus "
        "specifics and other technical details. Ivan shared a developer presentation "
        "with documentation and useful links. The host also discussed project ideas "
        "that could be built on GenLayer during the Hackathon.\n\n"
        "Speakers: @raskovsky",
        True,
    ),
    (
        "bradbury-builders-hackathon-launch",
        "Bradbury Builders Hackathon Launch",
        _at(2026, 3, 20, 13, 30),
        "https://x.com/i/broadcasts/1nxnRYADmgoxO",
        "The sponsors of the Hackathon, concurrently our validators, were introduced. "
        "Ivan also once again outlined the Hackathon conditions and emphasized the "
        "advantages of developing applications on GenLayer, including lifetime fees. "
        "To provide more context, existing solutions such as argue.fun, mergeproof.com, "
        "and others were showcased.\n\n"
        "Speakers: @raskovsky, Dasha from @stakeme_pro, Anton from @CroutonDigital, "
        "Patrick from @pathrock2, Albury from @chutes_ai",
        True,
    ),
    (
        "vibecoding-bradbury-gym",
        "GenLayer Vibecoding Series: Bradbury Gym",
        _at(2026, 4, 1, 16, 30),
        "https://x.com/i/broadcasts/1aKbdbyZdjqJX",
        "The session covered the main features and advantages of the Bradbury testnet, "
        "followed by a vibecoding demonstration of a benchmark running on GenLayer.\n\n"
        "Speakers: @raskovsky, @cognocracy",
        True,
    ),
    (
        "bradbury-hackathon-winners",
        "Bradbury Hackathon Winners Announcement",
        _at(2026, 4, 14, 14, 0),
        "https://x.com/i/broadcasts/1PKqrElvYVmGb",
        "Bradbury Hackathon Winners Review: Ivan presented a summary of the Hackathon "
        "results and showcased each winning project.\n\n"
        "Speakers: @raskovsky",
        True,
    ),
    (
        "bradbury-hackathon-demo-day",
        "Bradbury Hackathon Demo Day",
        _at(2026, 4, 17, 15, 0),
        "https://x.com/i/broadcasts/1AJEmOqRBoZJL",
        "Discussion with the teams behind BuildersClaw, AutoBounty, and TreasuryPilot — "
        "winners of the Bradbury Hackathon — including their backgrounds and demos of "
        "their applications.\n\n"
        "Speakers: @raskovsky, team @buildersclaw, @ArtuGrande (AutoBounty), "
        "@sandraupgrade (TreasuryPilot)",
        True,
    ),
    (
        "nov-2025-hackathon-submissions",
        "GenLayer November 2025 Hackathon — Live Submissions Review",
        _at(2025, 11, 14, 15, 15),
        "https://x.com/i/broadcasts/1ZkJzZygWndJv",
        "Live overview of GenLayer Hackathon applications.\n\n"
        "Speakers: @raskovsky",
        True,
    ),
    (
        "vibecoding-ep1",
        "GenLayer Vibecoding Series Episode 1: GenLayer Introduction & Basics",
        _at(2025, 12, 23, 14, 0),
        "https://x.com/i/broadcasts/1OdKrOvXjrYGX",
        "Vibecoding Series Episode 1. Ivan showcased GenLayer Studio and explained "
        "the structure of an intelligent contract.\n\n"
        "Speakers: @raskovsky",
        True,
    ),
    (
        "vibecoding-ep2",
        "GenLayer Vibecoding Series Episode 2: Our First Intelligent Contract",
        _at(2025, 12, 30, 14, 0),
        "https://x.com/i/broadcasts/1eaKbjQdYgrKX",
        "Vibecoding Series Episode 2. Setting up the Claude terminal, creating the "
        "first Intelligent Contract, testing it in Studio, and fixing bugs.\n\n"
        "Speakers: @raskovsky",
        True,
    ),
    (
        "vibecoding-ep3",
        "GenLayer Vibecoding Series Episode 3: From an Intelligent Contract to a DApp",
        _at(2026, 1, 7, 14, 0),
        "https://x.com/i/broadcasts/1ypJdqwnwPaxW",
        "Vibecoding Series Episode 3. Building a DApp by combining a contract and a "
        "frontend using the Claude terminal.\n\n"
        "Speakers: @raskovsky",
        True,
    ),
    (
        "vibecoding-ep4",
        "GenLayer Vibecoding Series Episode 4: Iterating, Polishing and Deploying",
        _at(2026, 1, 13, 14, 0),
        "https://x.com/i/broadcasts/1ypKdqgAWkpGW",
        "Vibecoding Series Episode 4. Continuing DApp moderation: editing and fixing "
        "bugs with the Claude terminal and GenLayer Studio.\n\n"
        "Speakers: @raskovsky",
        True,
    ),
    (
        "gentalks-ep1",
        "GenTalks Episode 1",
        _at(2026, 1, 21, 13, 30),
        "https://x.com/GenLayer/status/2013747638517047635",
        "",
        True,
    ),
    (
        "gentalks-ep2",
        "GenTalks Episode 2",
        _at(2026, 1, 28, 13, 30),
        "https://x.com/GenLayer/status/2016195968031396258",
        "",
        True,
    ),
    (
        "gentalks-ep3",
        "GenTalks Episode 3",
        _at(2026, 2, 5, 15, 30),
        "https://x.com/i/broadcasts/1ypKdqpXYLrGW",
        "Discussion of the current market landscape, emerging technologies such as "
        "OpenClaw, ClawBot, Moltbook, RentAHuman.ai, ClawTasks, Argue.fun, and ClawHub, "
        "and GenLayer's role. An IRL meetup in Ukraine was also discussed.\n\n"
        "Speakers: @raskovsky, @driudor",
        True,
    ),
    (
        "gentalks-ep4",
        "GenTalks Episode 4",
        _at(2026, 2, 11, 14, 30),
        "https://x.com/i/broadcasts/1MYxNlwjdyLGw",
        "Speakers: @raskovsky, @driudor",
        True,
    ),
    (
        "gentalks-ep5",
        "GenTalks Episode 5",
        _at(2026, 2, 25, 14, 30),
        "https://x.com/i/broadcasts/1yxBeMebmnYJN",
        "Introduction to Internet Court and Rally updates, as well as the Community "
        "section on the Portal, and the automatic submission review system. The "
        "discussion also included Argue.fun features for autonomous agents and "
        "introductions to Mergeproof.com and Molly.fun.\n\n"
        "Speakers: @raskovsky, @driudor",
        True,
    ),
    (
        "gentalks-ep6",
        "GenTalks Episode 6",
        _at(2026, 3, 4, 14, 30),
        "https://x.com/i/broadcasts/1DxleEVZyndKL",
        "Discussion of Rally.fun and Argue.fun, and the future role of autonomous "
        "agents in shaping the internet. Presentation of Botcha.xyz as a CAPTCHA "
        "solution designed for agents.\n\n"
        "Speakers: @raskovsky, @joaquinbressan",
        True,
    ),
    (
        "gentalks-ep7",
        "GenTalks Episode 7",
        _at(2026, 3, 11, 14, 30),
        "https://x.com/i/broadcasts/1rxmqoVaVWDxy",
        "Edgars spoke about what makes Bradbury stand out today, shared insights on "
        "validators, and discussed Argue.fun as a modern approach to dispute "
        "resolution.\n\n"
        "Speakers: @raskovsky, @driudor, @EdgarsNemse",
        True,
    ),
    (
        "gentalks-ep8",
        "GenTalks Episode 8",
        _at(2026, 3, 18, 14, 30),
        "https://x.com/i/broadcasts/1wxWjaZPpYnJQ",
        "First impressions from the Bradbury launch. Albert talked about his "
        "experience building on GenLayer and broke down the Developer Fee tokenomics. "
        "Review of skills.genlayer.com.\n\n"
        "Speakers: @raskovsky, @driudor, @kstellana",
        True,
    ),
    (
        "gentalks-ep9",
        "GenTalks Episode 9",
        _at(2026, 3, 25, 14, 30),
        "https://x.com/i/broadcasts/1qxvvkzNrbRxB",
        "A look at the latest stats and some Hackathon projects, followed by a "
        "discussion about the GenLayer Portal.\n\n"
        "Speakers: @raskovsky, @driudor",
        True,
    ),
    (
        "gentalks-ep10",
        "GenTalks Episode 10",
        _at(2026, 4, 1, 14, 30),
        "https://x.com/i/broadcasts/1RKZzjyvzAXKB",
        "David and Ivan discuss the current Hackathon results and the support "
        "provided to participating teams. They also review internetcourt.org, share "
        "thoughts on GenTalks, cover the latest Bradbury testnet news, and go over "
        "GenLayer Portal submission statistics.\n\n"
        "Speakers: @raskovsky, @driudor",
        True,
    ),
    (
        "gentalks-ep11",
        "GenTalks Episode 11",
        _at(2026, 4, 8, 14, 30),
        "https://x.com/i/broadcasts/1aJbdbBQLqoKX",
        "Overview of the GenLayer Hackathon submissions.\n\n"
        "Speakers: @raskovsky, @driudor",
        True,
    ),
    (
        "gentalks-ep12",
        "GenTalks Episode 12",
        _at(2026, 4, 15, 14, 30),
        "https://x.com/i/broadcasts/1rGmqolwYdqGy",
        "GenLayer Hackathon results and reviews of several projects. Answers to "
        "community questions. Introducing pmkit.courtofinternet.com, a tool for "
        "creating prediction markets.\n\n"
        "Speakers: @raskovsky, @driudor",
        True,
    ),
    (
        "gentalks-ep13",
        "GenTalks Episode 13",
        _at(2026, 4, 22, 14, 30),
        "https://x.com/i/broadcasts/1vJpPrpRaEQJE",
        "Announcement of an IRL event in Argentina hosted by Ivan. Discussions about "
        "builder meetups and plans from the GenLayer Foundation, including validator "
        "onboarding and more.\n\n"
        "Speakers: @raskovsky, @driudor",
        True,
    ),
    (
        "fud-markets-testnet-launch",
        "FUD Markets Testnet Launch Livestream",
        _at(2026, 5, 15, 15, 0),
        "https://x.com/GenLayer/status/2054659264912687394",
        "@raskovsky and @theboymarc0x's deep dive on the recently launched app FUD "
        "Markets that uses GenLayer's technology, their Testnet and Mainnet phases.\n\n"
        "Speakers: @raskovsky, @theboymarc0x",
        True,
    ),
]


def _image_url(slug: str, has_own_banner: bool) -> str:
    return f"{CLOUDINARY_BASE}/{slug}.png" if has_own_banner else DEFAULT_BANNER


def seed_streams(apps, schema_editor):
    Stream = apps.get_model("gen_tv", "Stream")
    for slug, title, starts_at, url, description, has_own_banner in STREAMS:
        Stream.objects.update_or_create(
            slug=slug,
            defaults={
                "title": title,
                "description": description,
                "url": url,
                "image_url": _image_url(slug, has_own_banner),
                "starts_at": starts_at,
                "ends_at": starts_at + DURATION,
                "category": "internal",
                "is_active": True,
            },
        )


def unseed_streams(apps, schema_editor):
    Stream = apps.get_model("gen_tv", "Stream")
    Stream.objects.filter(slug__in=[s[0] for s in STREAMS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("gen_tv", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_streams, unseed_streams),
    ]
