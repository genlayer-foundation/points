from django.db import migrations


def seed_featured_content(apps, schema_editor):
    User = apps.get_model('users', 'User')
    FeaturedContent = apps.get_model('contributions', 'FeaturedContent')

    albert = User.objects.get(email='albert@genlayer.foundation')  # cognocracy
    ivan = User.objects.get(email='ivan@genlayer.foundation')      # raskovsky

    FeaturedContent.objects.create(
        content_type='hero',
        title='Argue.fun Launch',
        description='Deploy intelligent contracts, run validators, and earn GenLayer Points on the latest testnet.',
        subtitle='cognocracy',
        user=albert,
        hero_image_url='https://res.cloudinary.com/dfqmoeawa/image/upload/v1772117991/tally/featured_1_hero_1772117989.png',
        hero_image_public_id='tally/featured_1_hero_1772117989',
        url='',
        is_active=True,
        order=0,
    )

    FeaturedContent.objects.create(
        content_type='build',
        title='Argue.fun',
        description='',
        subtitle='',
        user=albert,
        hero_image_url='https://res.cloudinary.com/dfqmoeawa/image/upload/v1772117992/tally/featured_2_hero_1772117992.png',
        hero_image_public_id='tally/featured_2_hero_1772117992',
        user_profile_image_url='https://res.cloudinary.com/dfqmoeawa/image/upload/v1772117994/tally/featured_2_avatar_1772117993.png',
        user_profile_image_public_id='tally/featured_2_avatar_1772117993',
        url='',
        is_active=True,
        order=0,
    )

    FeaturedContent.objects.create(
        content_type='build',
        title='Internet Court',
        description='',
        subtitle='',
        user=ivan,
        hero_image_url='https://res.cloudinary.com/dfqmoeawa/image/upload/v1772117994/tally/featured_3_hero_1772117994.png',
        hero_image_public_id='tally/featured_3_hero_1772117994',
        user_profile_image_url='https://res.cloudinary.com/dfqmoeawa/image/upload/v1772117995/tally/featured_3_avatar_1772117995.png',
        user_profile_image_public_id='tally/featured_3_avatar_1772117995',
        url='',
        is_active=True,
        order=1,
    )

    FeaturedContent.objects.create(
        content_type='build',
        title='Rally',
        description='',
        subtitle='',
        user=ivan,
        hero_image_url='https://res.cloudinary.com/dfqmoeawa/image/upload/v1772117996/tally/featured_4_hero_1772117995.png',
        hero_image_public_id='tally/featured_4_hero_1772117995',
        user_profile_image_url='https://res.cloudinary.com/dfqmoeawa/image/upload/v1772117996/tally/featured_4_avatar_1772117996.png',
        user_profile_image_public_id='tally/featured_4_avatar_1772117996',
        url='',
        is_active=True,
        order=2,
    )


def reverse_featured_content(apps, schema_editor):
    FeaturedContent = apps.get_model('contributions', 'FeaturedContent')
    FeaturedContent.objects.filter(
        title='Argue.fun Launch', content_type='hero'
    ).delete()
    FeaturedContent.objects.filter(
        title='Argue.fun', content_type='build'
    ).delete()
    FeaturedContent.objects.filter(
        title='Internet Court', content_type='build'
    ).delete()
    FeaturedContent.objects.filter(
        title='Rally', content_type='build'
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('contributions', '0036_alert'),
    ]

    operations = [
        migrations.RunPython(seed_featured_content, reverse_featured_content),
    ]
