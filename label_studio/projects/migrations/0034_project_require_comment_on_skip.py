from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0033_projects_soft_delete_indexes_async'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='require_comment_on_skip',
            field=models.BooleanField(
                default=True,
                help_text='Require annotators to provide skip reason when skipping a task',
                verbose_name='require comment on skip',
            ),
        ),
    ]
