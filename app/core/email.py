from brevo import AsyncBrevo
from brevo.transactional_emails import (
    SendTransacEmailRequestSender,
    SendTransacEmailRequestToItem,
)
from brevo.core.api_error import ApiError
from app.core.config import settings


async def send_magic_link(to_email: str, to_name: str, token: str):
    client = AsyncBrevo(api_key=settings.BREVO_API_KEY)

    verify_url = f"{settings.FRONTEND_BASE_URL}/auth/verify?token={token}"

    try:
        await client.transactional_emails.send_transac_email(
            subject="Activate your ICT Helpdesk account",
            html_content=f"""
                <p>Hi {to_name},</p>
                <p>Click the link below to complete your sign up.
                This link expires in 15 minutes.</p>
                <a href="{verify_url}">Verify my account</a>
                <p>If you didn't request this, ignore this email.</p>
            """,
            sender=SendTransacEmailRequestSender(
                email=settings.BREVO_SENDER_EMAIL,
                name=settings.BREVO_SENDER_NAME,
            ),
            to=[SendTransacEmailRequestToItem(email=to_email, name=to_name)],
        )
    except ApiError as e:
        raise RuntimeError(f"Brevo email failed: {e.status_code} - {e.body}")
    

async def send_password_reset(to_email: str, to_name: str, token: str):
    client = AsyncBrevo(api_key=settings.BREVO_API_KEY)

    reset_url = f"{settings.FRONTEND_BASE_URL}/auth/reset-password?token={token}"

    try:
        await client.transactional_emails.send_transac_email(
            subject="Reset your ICT Helpdesk password",
            html_content=f"""
                <p>Hi {to_name},</p>
                <p>Click the link below to reset your password.
                This link expires in 15 minutes.</p>
                <a href="{reset_url}">Reset my password</a>
                <p>If you didn't request this, ignore this email.</p>
            """,
            sender=SendTransacEmailRequestSender(
                email=settings.BREVO_SENDER_EMAIL,
                name=settings.BREVO_SENDER_NAME,
            ),
            to=[SendTransacEmailRequestToItem(email=to_email, name=to_name)],
        )
    except ApiError as e:
        raise RuntimeError(f"Brevo email failed: {e.status_code} - {e.body}")