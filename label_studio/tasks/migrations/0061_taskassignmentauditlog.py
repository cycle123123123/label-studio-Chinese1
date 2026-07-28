from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0033_projects_soft_delete_indexes_async'),
        ('tasks', '0060_taskassignment'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='TaskAssignmentAuditLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                (
                    'action',
                    models.CharField(
                        choices=[('assigned', 'Assigned'), ('reassigned', 'Reassigned'), ('unassigned', 'Unassigned')],
                        help_text='Assignment action type',
                        max_length=32,
                    ),
                ),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='Creation time', verbose_name='created at')),
                (
                    'assigned_by',
                    models.ForeignKey(
                        blank=True,
                        help_text='User who performed assignment action',
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='task_assignment_audit_as_actor',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    'assignee',
                    models.ForeignKey(
                        blank=True,
                        help_text='Current assignee after action',
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='task_assignment_audit_as_assignee',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    'previous_assignee',
                    models.ForeignKey(
                        blank=True,
                        help_text='Assignee before action',
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='task_assignment_audit_as_previous_assignee',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    'project',
                    models.ForeignKey(
                        help_text='Project of assignment action',
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='task_assignment_audit_logs',
                        to='projects.project',
                    ),
                ),
                (
                    'task',
                    models.ForeignKey(
                        help_text='Task affected by assignment action',
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='assignment_audit_logs',
                        to='tasks.task',
                    ),
                ),
            ],
            options={
                'db_table': 'task_assignment_audit_log',
            },
        ),
        migrations.AddIndex(
            model_name='taskassignmentauditlog',
            index=models.Index(fields=['project', '-created_at'], name='task_assign_project_dfaa7c_idx'),
        ),
        migrations.AddIndex(
            model_name='taskassignmentauditlog',
            index=models.Index(fields=['task', '-created_at'], name='task_assign_task_id_402550_idx'),
        ),
        migrations.AddIndex(
            model_name='taskassignmentauditlog',
            index=models.Index(fields=['assignee', '-created_at'], name='task_assign_assigne_85b20d_idx'),
        ),
    ]
