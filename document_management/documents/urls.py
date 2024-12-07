from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('login/', views.login, name='login'),
    path('upload/', views.upload_document, name='upload_document'),
    path('list/', views.list_documents, name='list_documents'),
    path('update/<uuid:document_id>/', views.update_document, name='update_document'),
    path('delete/<uuid:document_id>/', views.delete_document, name='delete_document'),
]

