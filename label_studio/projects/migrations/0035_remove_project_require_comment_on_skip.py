from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0034_project_require_comment_on_skip'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='project',
            name='require_comment_on_skip',
        ),
    ]
