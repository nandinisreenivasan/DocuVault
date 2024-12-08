from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from django.conf import settings
from .models import Document
from .serializers import DocumentSerializer
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from django.contrib.auth import get_user_model
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import check_password

import re
import uuid

User = get_user_model()


def validate_user_email(email):
    try:
        validate_email(email)
    except ValidationError:
        raise ValueError("Invalid email format")


def validate_password_strength(password):
    password_regex = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$")
    if not password_regex.match(password):
        raise ValueError(
            "Password must be at least 8 characters long, contain at least one uppercase letter, one lowercase letter, and one digit."
        )


def decode_jwt_token(token):
    try:
        decoded_token = AccessToken(token)
        return decoded_token
    except Exception as e:
        raise ValueError(f"Invalid or expired token: {str(e)}")


def detect_document_type(text):
    keywords = {
        "ID Card": ["id number", "date of birth"],
        "IRS Form": ["internal revenue service", "taxpayer id"],
        "Passport": ["passport number", "nationality"],
        "Bank Statement": ["account number", "transaction history"],
    }

    text = text.lower()
    for doc_type, terms in keywords.items():
        if any(re.search(term, text) for term in terms):
            return doc_type
    return "Unknown"


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def signup(request):
    email = request.data.get("email")
    password = request.data.get("password")

    if not email or not password:
        return Response(
            {"error": "Email and password are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        validate_user_email(email)
        if User.objects.filter(email=email).exists():
            return Response(
                {"error": "Email already registered"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        validate_password_strength(password)
        User.objects.create_user(email=email, password=password)
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    return Response({"message": "Signup successful"}, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def login(request):
    email = request.headers.get("email")
    password = request.headers.get("password")

    if not email or not password:
        return Response(
            {"error": "Email and password are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        user = User.objects.get(email=email)
        if not check_password(password, user.password):
            raise ValueError("Invalid email or password")
    except (User.DoesNotExist, ValueError):
        return Response(
            {"error": "Invalid email or password."}, status=status.HTTP_401_UNAUTHORIZED
        )

    refresh = RefreshToken.for_user(user)
    return Response(
        {
            "refresh_token": str(refresh),
            "access_token": str(refresh.access_token),
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def upload_document(request):
    email = request.headers.get("email")
    auth_token = request.headers.get("Authorization")

    if not email or not auth_token:
        return Response(
            {"error": "Email and Authorization headers are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        token = auth_token.split(" ")[1]
        decoded_token = decode_jwt_token(token)
        user_id = decoded_token["user_id"]
        user = User.objects.get(email=email)
        if user.id != user_id:
            return Response(
                {"error": "Email does not match the token's user."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
    except (IndexError, ValueError, User.DoesNotExist) as e:
        return Response({"error": str(e)}, status=status.HTTP_401_UNAUTHORIZED)

    text = request.data.get("text")
    pages = request.data.get("pages")
    tags = request.data.get("tags", [])

    if not text or not isinstance(text, str) or not text.strip():
        return Response(
            {"error": "Text must be a non-empty string."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not pages or not isinstance(pages, int) or pages <= 0:
        return Response(
            {"error": "Pages must be a positive integer."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    doc_type = detect_document_type(text)
    document = Document.objects.create(
        uuid=uuid.uuid4(),
        pages=pages,
        text=text,
        tags=tags,
        doc_type=doc_type,
        uploaded_by=user,
    )

    serializer = DocumentSerializer(document)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def list_documents(request):
    email = request.headers.get("email")
    auth_token = request.headers.get("Authorization")

    if not email or not auth_token:
        return Response(
            {"error": "Email and Authorization headers are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        token = auth_token.split(" ")[1]
        decoded_token = decode_jwt_token(token)
        user_id = decoded_token["user_id"]
        user = User.objects.get(email=email)
        if user.id != user_id:
            return Response(
                {"error": "Email does not match the token's user."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
    except (IndexError, ValueError, User.DoesNotExist) as e:
        return Response({"error": str(e)}, status=status.HTTP_401_UNAUTHORIZED)

    documents = Document.objects.filter(uploaded_by=user)
    tags_filter = request.query_params.get("tags", None)
    if tags_filter:
        tags_filter = tags_filter.lower()
        documents = documents.filter(tags__contains=[tags_filter])

    try:
        page_size = int(
            request.query_params.get("page_size", settings.DEFAULT_PAGE_SIZE)
        )
        page_number = int(
            request.query_params.get("page", settings.DEFAULT_PAGE_NUMBER)
        )
        start_index = (page_number - 1) * page_size
        end_index = page_number * page_size
        documents = documents[start_index:end_index]
    except ValueError:
        return Response(
            {"error": "Pagination parameters must be integers."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    total_documents = Document.objects.filter(uploaded_by=user)
    if tags_filter:
        total_documents = total_documents.filter(tags__contains=[tags_filter])
    total_count = total_documents.count()

    serializer = DocumentSerializer(documents, many=True)
    response_data = {
        "total_count": total_count,
        "page_size": page_size,
        "page_number": page_number,
        "total_pages": (total_count + page_size - 1) // page_size,
        "documents": serializer.data,
    }

    return Response(response_data, status=status.HTTP_200_OK)


@api_view(["PUT"])
@permission_classes([permissions.IsAuthenticated])
def update_document(request, document_id):
    email = request.headers.get("email")
    auth_token = request.headers.get("Authorization")

    if not email or not auth_token:
        return Response(
            {"error": "Email and Authorization headers are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        token = auth_token.split(" ")[1]
        decoded_token = decode_jwt_token(token)
        user_id = decoded_token.get("user_id")
        if not user_id:
            return Response(
                {"error": "Token does not contain user_id"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
    except (IndexError, ValueError) as e:
        return Response(
            {"error": "Invalid authorization token format"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    try:
        user = User.objects.get(email=email)
        if user.id != user_id:
            return Response(
                {"error": "Email does not match the token's user."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
    except User.DoesNotExist:
        return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

    try:
        document = Document.objects.get(uuid=document_id, uploaded_by_id=user_id)
    except Document.DoesNotExist:
        return Response(
            {"error": f"Document with id {document_id} not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    document.tags = request.data.get("tags", document.tags)
    document.save()

    serializer = DocumentSerializer(document)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["DELETE"])
@permission_classes([permissions.IsAuthenticated])
def delete_document(request, document_id):
    email = request.headers.get("email")
    auth_token = request.headers.get("Authorization")

    if not email or not auth_token:
        return Response(
            {"error": "Email and Authorization headers are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        token = auth_token.split(" ")[1]
        decoded_token = decode_jwt_token(token)
        user_id = decoded_token["user_id"]
        user = User.objects.get(email=email)
        if user.id != user_id:
            return Response(
                {"error": "Email does not match the token's user."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            document = Document.objects.get(uuid=document_id, uploaded_by_id=user_id)
            document.delete()
        except Document.DoesNotExist:
            return Response(
                {"error": f"Document with id {document_id} not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

    except (IndexError, ValueError, Document.DoesNotExist) as e:
        return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

    return Response(
        {"message": "Document deleted successfully"}, status=status.HTTP_204_NO_CONTENT
    )
