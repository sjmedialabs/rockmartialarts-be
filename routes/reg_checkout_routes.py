from fastapi import APIRouter

from controllers.reg_checkout_controller import RegCheckoutController
from models.reg_checkout_models import (
    CreateRegOrderBody,
    RenewalCronBody,
    SendOtpBody,
    VerifyOtpBody,
    VerifyRegPaymentBody,
)

router = APIRouter()


@router.post("/send-otp")
async def reg_send_otp(body: SendOtpBody):
    return await RegCheckoutController.send_otp(body.phone)


@router.post("/verify-otp")
async def reg_verify_otp(body: VerifyOtpBody):
    return await RegCheckoutController.verify_otp(body)


@router.post("/create-order")
async def reg_create_order(body: CreateRegOrderBody):
    return await RegCheckoutController.create_order(body)


@router.post("/verify-payment")
async def reg_verify_payment(body: VerifyRegPaymentBody):
    return await RegCheckoutController.verify_payment(body)


@router.post("/cron/renewal-reminders")
async def reg_renewal_reminders(body: RenewalCronBody):
    return await RegCheckoutController.run_renewal_reminders(body.secret)
