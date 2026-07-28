from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('tasks', '0061_taskassignmentauditlog'),
    ]

    operations = [
        migrations.RenameIndex(
            model_name='taskassignment',
            new_name='task_assign_user_id_a2b7b4_idx',
            old_name='task_assignm_user_id_7fffd2_idx',
        ),
        migrations.RenameIndex(
            model_name='taskassignment',
            new_name='task_assign_task_id_2621c3_idx',
            old_name='task_assignm_task_id_72a32f_idx',
        ),
    ]
