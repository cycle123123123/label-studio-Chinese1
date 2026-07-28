from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('tasks', '0059_task_completion_id_updated_at_idx_async'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='TaskAssignment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='Creation time', verbose_name='created at')),
                (
                    'assigned_by',
                    models.ForeignKey(
                        blank=True,
                        help_text='User who assigned the task',
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='created_task_assignments',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    'task',
                    models.OneToOneField(
                        help_text='Assigned task',
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='assignment',
                        to='tasks.task',
                    ),
                ),
                (
                    'user',
                    models.ForeignKey(
                        help_text='Assigned user',
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='task_assignments',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'db_table': 'task_assignment',
            },
        ),
        migrations.AddIndex(
            model_name='taskassignment',
            index=models.Index(fields=['user', 'task'], name='task_assignm_user_id_7fffd2_idx'),
        ),
        migrations.AddIndex(
            model_name='taskassignment',
            index=models.Index(fields=['task', 'user'], name='task_assignm_task_id_72a32f_idx'),
        ),
    ]
