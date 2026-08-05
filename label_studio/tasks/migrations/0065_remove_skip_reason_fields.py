from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('tasks', '0064_taskworkflowauditlog_add_submitted_action'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='annotation',
            name='skip_reason',
        ),
        migrations.RemoveField(
            model_name='taskworkflowauditlog',
            name='reason',
        ),
    ]
