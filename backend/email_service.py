import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
NUTRITIONIST_EMAIL = os.environ.get("NUTRITIONIST_EMAIL", "inesbandarranutricao@gmail.com")
SITE_URL = os.environ.get("SITE_URL", "https://ibnutricao.pt")
# Display name shown to recipients, and where replies go by default. With a noreply
# sender (e.g. ibnutricao.noreply@gmail.com) this routes replies to a monitored inbox.
MAIL_FROM_NAME = os.environ.get("MAIL_FROM_NAME", "IB Nutrição")
REPLY_TO = os.environ.get("REPLY_TO", NUTRITIONIST_EMAIL)
# The visible "From"/envelope sender address. With a transactional provider the SMTP
# login (SMTP_USER, e.g. "resend") differs from the sender address, so this is separate.
# Defaults to SMTP_USER for plain Gmail where they're the same.
MAIL_FROM = os.environ.get("MAIL_FROM", SMTP_USER)

_WEEKDAYS = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
_MONTHS = ["", "janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]


def _fmt_date(d):
    return f"{_WEEKDAYS[d.weekday()]}, {d.day} de {_MONTHS[d.month]} de {d.year}"


def _send(to, subject, html, reply_to=None):
    if not SMTP_USER or not SMTP_PASS:
        print(f"[Email] (no SMTP configured) Would send to {to}: {subject}")
        return
    msg = MIMEMultipart("alternative")
    msg["From"] = f"{MAIL_FROM_NAME} <{MAIL_FROM}>"
    msg["To"] = to
    reply_addr = reply_to or REPLY_TO
    if reply_addr:
        msg["Reply-To"] = reply_addr
    msg["Subject"] = subject
    msg.attach(MIMEText(html, "html"))
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(MAIL_FROM, to, msg.as_string())
    except Exception as e:
        print(f"[Email] Send error: {e}")


def _base_style():
    return f"""
    <div style="font-family:'Jost',sans-serif;color:#2C1A1A;max-width:600px;margin:auto;background:#FDF7F7;border-radius:12px;padding:32px;">
    <div style="text-align:center;margin-bottom:24px;">
      <img src="{SITE_URL}/images/vermelho.png" alt="IB Nutrição" width="140"
           style="max-width:140px;height:auto;display:inline-block;border:0;outline:none;text-decoration:none;" />
    </div>
    """


def _booking_detail_block(booking):
    regime_info = booking.regime
    if booking.local_consulta:
        regime_info = f"{booking.regime} — {booking.local_consulta}"
    dur = "1h30m" if booking.duration_minutes == 90 else "1h"
    return f"""
    <div style="background:white;border-radius:8px;padding:20px;margin:16px 0;border-left:4px solid #B94448;">
      <table style="width:100%;border-collapse:collapse;">
        <tr><td style="padding:5px 0;color:#7A5050;font-size:0.85rem;width:120px;">Referência</td>
            <td style="padding:5px 0;font-weight:600;font-size:1.1rem;color:#B94448;">{booking.reference}</td></tr>
        <tr><td style="padding:5px 0;color:#7A5050;font-size:0.85rem;">Data</td>
            <td style="padding:5px 0;">{_fmt_date(booking.slot_date)}</td></tr>
        <tr><td style="padding:5px 0;color:#7A5050;font-size:0.85rem;">Hora</td>
            <td style="padding:5px 0;">{booking.slot_time.strftime('%H:%M')}</td></tr>
        <tr><td style="padding:5px 0;color:#7A5050;font-size:0.85rem;">Duração</td>
            <td style="padding:5px 0;">{dur}</td></tr>
        <tr><td style="padding:5px 0;color:#7A5050;font-size:0.85rem;">Consulta</td>
            <td style="padding:5px 0;">{booking.tipo_consulta}</td></tr>
        <tr><td style="padding:5px 0;color:#7A5050;font-size:0.85rem;">Regime</td>
            <td style="padding:5px 0;">{regime_info}</td></tr>
        <tr><td style="padding:5px 0;color:#7A5050;font-size:0.85rem;">Preço</td>
            <td style="padding:5px 0;font-weight:600;">{float(booking.price):.0f}€</td></tr>
      </table>
    </div>
    """


def send_booking_confirmation(booking):
    html = _base_style() + f"""
    <h2 style="font-family:Georgia,serif;font-weight:400;color:#2C1A1A;">Consulta Confirmada</h2>
    <p>Olá <strong>{booking.nome}</strong>,</p>
    <p>A sua consulta foi marcada com sucesso. Guarde os detalhes abaixo.</p>
    {_booking_detail_block(booking)}
    <p>Para verificar, alterar ou cancelar a sua consulta, aceda a
       <a href="{SITE_URL}/marcar-consulta" style="color:#B94448;">{SITE_URL}/marcar-consulta</a>
       e use a referência <strong>{booking.reference}</strong> com este email.</p>
    <p style="color:#7A5050;font-size:0.85rem;">Pedimos que eventuais cancelamentos sejam feitos com pelo menos 24 horas de antecedência.</p>
    <p>Com os melhores cumprimentos,<br><strong>Inês Bandarra</strong><br>
       <span style="color:#7A5050;font-size:0.85rem;">Materno-Infantil &amp; Nutricionista Pediátrica</span></p>
    </div>
    """
    _send(booking.email, f"Consulta Confirmada — {booking.reference}", html)


def send_booking_updated_client(booking):
    html = _base_style() + f"""
    <h2 style="font-family:Georgia,serif;font-weight:400;color:#2C1A1A;">Consulta Atualizada</h2>
    <p>Olá <strong>{booking.nome}</strong>,</p>
    <p>Os detalhes da tua consulta foram atualizados. Confirma abaixo os novos dados.</p>
    {_booking_detail_block(booking)}
    <p>Se algo não estiver correto, responde a este email ou contacta-nos.</p>
    <p>Com os melhores cumprimentos,<br><strong>Inês Bandarra</strong></p>
    </div>
    """
    _send(booking.email, f"Consulta Atualizada — {booking.reference}", html)


def send_nutritionist_new_booking(booking):
    regime_info = booking.regime
    if booking.local_consulta:
        regime_info = f"{booking.regime} — {booking.local_consulta}"
    ctx = f"<tr><td style='padding:5px 0;color:#7A5050;font-size:0.85rem;'>Contexto</td><td style='padding:5px 0;'>{booking.contexto}</td></tr>" if booking.contexto else ""
    html = _base_style() + f"""
    <h2 style="font-family:Georgia,serif;font-weight:400;color:#B94448;">Nova Marcação Recebida</h2>
    {_booking_detail_block(booking)}
    <div style="background:white;border-radius:8px;padding:20px;margin:16px 0;">
      <table style="width:100%;border-collapse:collapse;">
        <tr><td style="padding:5px 0;color:#7A5050;font-size:0.85rem;width:120px;">Nome</td>
            <td style="padding:5px 0;font-weight:600;">{booking.nome}</td></tr>
        <tr><td style="padding:5px 0;color:#7A5050;font-size:0.85rem;">Idade</td>
            <td style="padding:5px 0;">{booking.idade} anos</td></tr>
        <tr><td style="padding:5px 0;color:#7A5050;font-size:0.85rem;">Email</td>
            <td style="padding:5px 0;">{booking.email}</td></tr>
        <tr><td style="padding:5px 0;color:#7A5050;font-size:0.85rem;">Contacto</td>
            <td style="padding:5px 0;">{booking.contacto}</td></tr>
        {ctx}
      </table>
    </div>
    </div>
    """
    _send(NUTRITIONIST_EMAIL, f"Nova Marcação — {booking.reference} — {booking.nome}", html, reply_to=booking.email)


def send_booking_cancelled_client(booking):
    html = _base_style() + f"""
    <h2 style="font-family:Georgia,serif;font-weight:400;color:#2C1A1A;">Consulta Cancelada</h2>
    <p>Olá <strong>{booking.nome}</strong>,</p>
    <p>A sua consulta <strong style="color:#B94448;">{booking.reference}</strong> foi cancelada com sucesso.</p>
    <p>Para marcar uma nova consulta, visite
       <a href="{SITE_URL}/marcar-consulta" style="color:#B94448;">{SITE_URL}/marcar-consulta</a>.</p>
    <p>Com os melhores cumprimentos,<br><strong>Inês Bandarra</strong></p>
    </div>
    """
    _send(booking.email, f"Consulta Cancelada — {booking.reference}", html)


def send_nutritionist_cancellation(booking):
    html = _base_style() + f"""
    <h2 style="font-family:Georgia,serif;font-weight:400;color:#B94448;">Cancelamento de Consulta</h2>
    <p>A seguinte consulta foi cancelada pelo cliente:</p>
    {_booking_detail_block(booking)}
    <p><strong>Nome:</strong> {booking.nome} &nbsp;|&nbsp; <strong>Email:</strong> {booking.email} &nbsp;|&nbsp; <strong>Contacto:</strong> {booking.contacto}</p>
    </div>
    """
    _send(NUTRITIONIST_EMAIL, f"Cancelamento — {booking.reference} — {booking.nome}", html, reply_to=booking.email)


def send_contact_message(name, email, phone, subject, message):
    phone_row = f"<tr><td style='padding:5px 0;color:#7A5050;font-size:0.85rem;width:100px;'>Telefone</td><td style='padding:5px 0;'>{phone}</td></tr>" if phone else ""
    html = _base_style() + f"""
    <h2 style="font-family:Georgia,serif;font-weight:400;color:#B94448;">Nova Mensagem de Contacto</h2>
    <div style="background:white;border-radius:8px;padding:20px;margin:16px 0;border-left:4px solid #B94448;">
      <table style="width:100%;border-collapse:collapse;">
        <tr><td style="padding:5px 0;color:#7A5050;font-size:0.85rem;width:100px;">Nome</td>
            <td style="padding:5px 0;font-weight:600;">{name}</td></tr>
        <tr><td style="padding:5px 0;color:#7A5050;font-size:0.85rem;">Email</td>
            <td style="padding:5px 0;">{email}</td></tr>
        {phone_row}
        <tr><td style="padding:5px 0;color:#7A5050;font-size:0.85rem;">Assunto</td>
            <td style="padding:5px 0;">{subject}</td></tr>
      </table>
    </div>
    <div style="background:white;border-radius:8px;padding:20px;margin:16px 0;">
      <p style="color:#7A5050;font-size:0.85rem;margin-bottom:8px;">Mensagem:</p>
      <p style="white-space:pre-wrap;line-height:1.6;">{message}</p>
    </div>
    <p style="color:#7A5050;font-size:0.85rem;">Para responder, escreva diretamente para <a href="mailto:{email}" style="color:#B94448;">{email}</a>.</p>
    </div>
    """
    _send(NUTRITIONIST_EMAIL, f"Contacto — {name} — {subject}", html, reply_to=email)


def send_nutritionist_edit_request(booking, edit_message):
    html = _base_style() + f"""
    <h2 style="font-family:Georgia,serif;font-weight:400;color:#B94448;">Pedido de Alteração</h2>
    <p>O cliente com a referência <strong>{booking.reference}</strong> solicitou uma alteração à sua consulta.</p>
    {_booking_detail_block(booking)}
    <div style="background:white;border-radius:8px;padding:20px;margin:16px 0;border-left:4px solid #F1BEBF;">
      <p style="color:#7A5050;font-size:0.85rem;margin-bottom:8px;">Mensagem do cliente:</p>
      <p style="font-style:italic;">{edit_message}</p>
    </div>
    <p><strong>Contacto:</strong> {booking.email} / {booking.contacto}</p>
    <p>Por favor entre em contacto com o cliente para confirmar a alteração.</p>
    </div>
    """
    _send(NUTRITIONIST_EMAIL, f"Pedido de Alteração — {booking.reference} — {booking.nome}", html, reply_to=booking.email)
