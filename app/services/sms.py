"""
SMS dispatch via TalkSasa BulkSMS.
API docs: https://bulksms.talksasa.com/api/v3/sms/send
"""
import logging
import httpx
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

TALKSASA_API_URL = "https://bulksms.talksasa.com/api/v3/sms/send"


async def send_sms_talksasa(phone: str, message: str) -> bool:
    """
    Send one SMS via TalkSasa.
    Phone must be in international format without +: 254712345678
    """
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                TALKSASA_API_URL,
                headers={
                    "Authorization": f"Bearer {settings.TALKSASA_API_KEY}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json={
                    "recipient": phone,
                    "sender_id": settings.TALKSASA_SENDER_ID,
                    "type": "plain",
                    "message": message,
                },
            )
            body = resp.json()
            if body.get("status") == "success":
                logger.info("TalkSasa SMS sent to %s", phone)
                return True
            logger.warning("TalkSasa SMS failed: %s", body.get("message"))
            return False
    except httpx.HTTPError as exc:
        logger.error("TalkSasa HTTP error for %s: %s", phone, exc)
        return False


async def send_sms(phone: str, message: str) -> bool:
    """Unified dispatcher — normalises phone number then sends."""
    if not phone:
        logger.warning("send_sms called with empty phone — skipping")
        return False

    # Normalise to international format WITHOUT + (TalkSasa format: 254XXXXXXXXX)
    phone = phone.strip().replace(" ", "").replace("-", "")
    if phone.startswith("+"):
        phone = phone[1:]                    # strip leading +
    elif phone.startswith("07") or phone.startswith("01"):
        phone = "254" + phone[1:]            # 0712345678 → 254712345678
    elif not phone.startswith("254"):
        phone = "254" + phone                # fallback

    if not settings.TALKSASA_API_KEY:
        logger.warning("TALKSASA_API_KEY not set — SMS not sent to %s", phone)
        return False

    return await send_sms_talksasa(phone, message)


async def send_bulk_sms(phones: list[str], message: str) -> bool:
    """
    Send one message to multiple numbers in a single API call.
    TalkSasa accepts comma-separated recipients.
    """
    if not phones:
        return False

    # Normalise all numbers
    normalised = []
    for phone in phones:
        phone = phone.strip().replace(" ", "").replace("-", "")
        if phone.startswith("+"):
            phone = phone[1:]
        elif phone.startswith("07") or phone.startswith("01"):
            phone = "254" + phone[1:]
        elif not phone.startswith("254"):
            phone = "254" + phone
        normalised.append(phone)

    recipient_str = ",".join(normalised)

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                TALKSASA_API_URL,
                headers={
                    "Authorization": f"Bearer {settings.TALKSASA_API_KEY}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json={
                    "recipient": recipient_str,
                    "sender_id": settings.TALKSASA_SENDER_ID,
                    "type": "plain",
                    "message": message,
                },
            )
            body = resp.json()
            if body.get("status") == "success":
                logger.info("TalkSasa bulk SMS sent to %d numbers", len(normalised))
                return True
            logger.warning("TalkSasa bulk SMS failed: %s", body.get("message"))
            return False
    except httpx.HTTPError as exc:
        logger.error("TalkSasa bulk SMS error: %s", exc)
        return False


# ── Message templates ─────────────────────────────────────────────────

def reminder_message(patient_name: str, medicine: str | None = None) -> str:
    base = f"Hi {patient_name}, this is your DawaTrack medication reminder."
    if medicine:
        base += f" Please take your {medicine}."
    base += " Log it at dawatrack.com. Stay healthy!"
    return base


def urgent_note_message(patient_name: str, doctor_name: str) -> str:
    return (
        f"Hi {patient_name}, {doctor_name} has sent you an urgent message "
        f"on DawaTrack. Please log in at dawatrack.com to read it."
    )