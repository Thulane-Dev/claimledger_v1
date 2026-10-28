
from django.urls import path
from .import views

app_name = "projects"

urlpatterns = [
    path('create-project', views.create_project, name='create-project'),
    path('projects/',views.ProjectsView, name='projects'),
    path('project/<uuid:project_uuid>/',views.ProjectDetailsVieW, name='project'),
    path('update-project/<uuid:project_uuid>/',views.update_project_view, name='update-project'),
    path("projects/<uuid:project_uuid>/delete/",views.delete_project,name="delete_project",),
]
