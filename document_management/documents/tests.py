import uuid
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import Document

User = get_user_model()


class DocuVaultTest(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com", password="Test@1234"
        )
        self.signup_url = reverse("signup")
        self.login_url = reverse("login")
        self.upload_document_url = reverse("upload_document")
        self.list_documents_url = reverse("list_documents")
        self.update_document_url = lambda doc_id: reverse(
            "update_document", args=[doc_id]
        )
        self.delete_document_url = lambda doc_id: reverse(
            "delete_document", args=[doc_id]
        )

    def authenticate_user(self):
        response = self.client.get(
            self.login_url, HTTP_EMAIL="test@example.com", HTTP_PASSWORD="Test@1234"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.access_token = response.data["access_token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")

    def test_signup(self):
        payload = {"email": "newuser@example.com", "password": "NewUser@123"}
        response = self.client.post(self.signup_url, data=payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("Signup successful", response.data["message"])

    def test_signup_with_invalid_email(self):
        payload = {"email": "invalid-email", "password": "Password@123"}
        response = self.client.post(self.signup_url, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid email format", response.data["error"])

    def test_signup_with_weak_password(self):
        payload = {"email": "newuser@example.com", "password": "weakpassword"}
        response = self.client.post(self.signup_url, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Password must be at least 8 characters long", response.data["error"]
        )

    def test_signup_with_existing_email(self):
        payload = {"email": "test@example.com", "password": "Test@1234"}
        response = self.client.post(self.signup_url, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Email already registered", response.data["error"])

    def test_login(self):
        response = self.client.get(
            self.login_url, HTTP_EMAIL="test@example.com", HTTP_PASSWORD="Test@1234"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", response.data)

    def test_login_with_invalid_email(self):
        response = self.client.get(
            self.login_url,
            HTTP_EMAIL="invalid@example.com",
            HTTP_PASSWORD="WrongPassword@123",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("Invalid email or password.", response.data["error"])

    def test_login_with_invalid_password(self):
        response = self.client.get(
            self.login_url,
            HTTP_EMAIL="test@example.com",
            HTTP_PASSWORD="WrongPassword@123",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("Invalid email or password.", response.data["error"])

    def test_upload_document(self):
        self.authenticate_user()
        payload = {
            "text": "This is a sample nationality document.",
            "pages": 2,
            "tags": ["sample"],
        }
        response = self.client.post(
            self.upload_document_url,
            data=payload,
            format="json",
            HTTP_EMAIL="test@example.com",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["doc_type"], "Passport")

    def test_upload_document_unauthenticated(self):
        payload = {"text": "This is a test document.", "pages": 1, "tags": ["sample"]}
        response = self.client.post(
            self.upload_document_url, data=payload, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("detail", response.data)

    def test_upload_document_invalid_payload(self):
        self.authenticate_user()
        payload = {"text": "", "pages": -1, "tags": "sample"}
        response = self.client.post(
            self.upload_document_url,
            data=payload,
            format="json",
            HTTP_EMAIL="test@example.com",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Text must be a non-empty string.", response.data["error"])

    def test_upload_document_with_invalid_token(self):
        invalid_token = "InvalidToken"
        payload = {"text": "Sample document", "pages": 2, "tags": ["sample"]}
        response = self.client.post(
            self.upload_document_url,
            data=payload,
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {invalid_token}",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("detail", response.data)
        self.assertEqual(
            response.data["detail"], "Given token not valid for any token type"
        )

    def test_upload_document_missing_fields(self):
        self.authenticate_user()
        payload = {"pages": -1, "tags": ["sample"]}
        response = self.client.post(
            self.upload_document_url,
            data=payload,
            format="json",
            HTTP_EMAIL="test@example.com",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Text must be a non-empty string.", response.data["error"])

    def test_list_documents(self):
        self.authenticate_user()
        Document.objects.create(
            uuid=uuid.uuid4(),
            pages=3,
            text="Sample text for Bank Statement.",
            tags=["bank", "statement"],
            doc_type="Bank Statement",
            uploaded_by=self.user,
        )
        response = self.client.get(
            self.list_documents_url, HTTP_EMAIL="test@example.com"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_count"], 1)

    def test_list_documents_without_token(self):
        response = self.client.get(
            self.list_documents_url, HTTP_EMAIL="test@example.com"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("detail", response.data)

    def test_list_documents_invalid_pagination(self):
        self.authenticate_user()
        Document.objects.create(
            uuid=uuid.uuid4(),
            pages=3,
            text="Sample text for Bank Statement.",
            tags=["bank", "statement"],
            doc_type="Bank Statement",
            uploaded_by=self.user,
        )
        response = self.client.get(
            self.list_documents_url,
            HTTP_EMAIL="test@example.com",
            data={"page_size": "invalid", "page": "1"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Pagination parameters must be integers.", response.data["error"])

    def test_update_document(self):
        self.authenticate_user()
        document = Document.objects.create(
            uuid=uuid.uuid4(),
            pages=1,
            text="Sample text",
            tags=["bank"],
            doc_type="ID Card",
            uploaded_by=self.user,
        )
        payload = {"tags": ["updated", "tag"]}
        response = self.client.put(
            self.update_document_url(document.uuid),
            data=payload,
            format="json",
            HTTP_EMAIL="test@example.com",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("updated", response.data["tags"])
        self.assertIn("tag", response.data["tags"])

    def test_update_document_unauthorized(self):
        other_user = User.objects.create_user(
            email="otheruser@example.com", password="OtherUser@1234"
        )
        document = Document.objects.create(
            uuid=uuid.uuid4(),
            pages=1,
            text="Sample text.",
            tags=["sample"],
            doc_type="ID Card",
            uploaded_by=other_user,
        )
        self.authenticate_user()
        payload = {"tags": ["updated"]}
        response = self.client.put(
            self.update_document_url(document.uuid),
            data=payload,
            format="json",
            HTTP_EMAIL="test@example.com",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            f"Document with id {document.uuid} not found.", response.data["error"]
        )

    def test_update_document_no_permission(self):
        other_user = User.objects.create_user(
            email="otheruser@example.com", password="OtherUser@1234"
        )
        document = Document.objects.create(
            uuid=uuid.uuid4(),
            pages=1,
            text="Sample text",
            tags=["bank"],
            doc_type="ID Card",
            uploaded_by=other_user,
        )
        self.authenticate_user()
        payload = {"tags": ["updated", "tag"]}
        response = self.client.put(
            self.update_document_url(document.uuid),
            data=payload,
            format="json",
            HTTP_EMAIL="test@example.com",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn(
            f"Document with id {document.uuid} not found.", response.data["error"]
        )

    def test_delete_document(self):
        self.authenticate_user()
        document = Document.objects.create(
            uuid=uuid.uuid4(),
            pages=1,
            text="Sample text.",
            tags=["sample"],
            doc_type="ID Card",
            uploaded_by=self.user,
        )
        response = self.client.delete(
            self.delete_document_url(document.uuid), HTTP_EMAIL="test@example.com"
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Document.objects.filter(uuid=document.uuid).exists())

    def test_delete_document_unauthorized(self):
        other_user = User.objects.create_user(
            email="otheruser@example.com", password="OtherUser@1234"
        )
        document = Document.objects.create(
            uuid=uuid.uuid4(),
            pages=1,
            text="Sample text.",
            tags=["sample"],
            doc_type="ID Card",
            uploaded_by=other_user,
        )
        self.authenticate_user()
        response = self.client.delete(
            self.delete_document_url(document.uuid), HTTP_EMAIL="test@example.com"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            f"Document with id {document.uuid} not found.", response.data["error"]
        )

    def test_delete_document_nonexistent(self):
        self.authenticate_user()
        fake_uuid = uuid.uuid4()
        response = self.client.delete(
            self.delete_document_url(fake_uuid), HTTP_EMAIL="test@example.com"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            f"Document with id {fake_uuid} not found.", response.data["error"]
        )

    def test_delete_document_forbidden(self):
        other_user = User.objects.create_user(
            email="otheruser@example.com", password="OtherUser@1234"
        )
        document = Document.objects.create(
            uuid=uuid.uuid4(),
            pages=1,
            text="Sample text.",
            tags=["sample"],
            doc_type="ID Card",
            uploaded_by=other_user,
        )
        self.authenticate_user()

        response = self.client.delete(
            self.delete_document_url(document.uuid), HTTP_EMAIL="test@example.com"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            f"Document with id {document.uuid} not found.",
            response.data["error"],
        )
