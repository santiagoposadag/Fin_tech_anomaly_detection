"""
Authentication Services - JWT, Password Hashing, Email
Implementación de servicios de infraestructura para autenticación

Cumple Dependency Inversion: Los casos de uso dependen de interfaces abstractas
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
import aiosmtplib
from email.message import EmailMessage
import secrets
import logging

logger = logging.getLogger(__name__)


class PasswordService:
    """
    Servicio para hashear y verificar contraseñas
    Utiliza bcrypt para máxima seguridad
    """
    
    def hash_password(self, password: str) -> str:
        """Hashea una contraseña usando bcrypt"""
        # Generar salt y hashear
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verifica que la contraseña coincida con el hash"""
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )


class JWTService:
    """
    Servicio para crear y verificar tokens JWT
    """
    
    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30
    ):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
    
    def create_access_token(
        self,
        data: dict,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Crea un token JWT
        
        Args:
            data: Datos a incluir en el token (ej: {"sub": "user_id"})
            expires_delta: Tiempo de expiración opcional
            
        Returns:
            Token JWT como string
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=self.access_token_expire_minutes
            )
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode,
            self.secret_key,
            algorithm=self.algorithm
        )
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[dict]:
        """
        Verifica y decodifica un token JWT
        
        Args:
            token: Token JWT a verificar
            
        Returns:
            Payload del token si es válido, None si es inválido
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            return payload
        except JWTError:
            return None


class EmailService:
    """
    Servicio para envío de correos electrónicos
    Utiliza SMTP de Gmail con contraseña de aplicación
    """
    
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_username: str,
        smtp_password: str,
        from_email: str,
        use_tls: bool = True
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.from_email = from_email
        self.use_tls = use_tls
    
    async def send_verification_email(
        self,
        to_email: str,
        user_name: str,
        verification_token: str,
        base_url: str
    ) -> bool:
        """
        Envía un correo de verificación al usuario
        
        Args:
            to_email: Email del destinatario
            user_name: Nombre del usuario
            verification_token: Token de verificación
            base_url: URL base de la aplicación
            
        Returns:
            True si se envió correctamente, False en caso contrario
        """
        try:
            message = EmailMessage()
            message["From"] = self.from_email
            message["To"] = to_email
            message["Subject"] = "Verifica tu cuenta - FinTech Bank"
            
            # Plantilla HTML profesional con el código de verificación
            html_body = f"""
            <!DOCTYPE html>
            <html lang="es">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Verificación de Cuenta</title>
            </head>
            <body style="margin: 0; padding: 0; font-family: 'Arial', sans-serif; background-color: #f4f7fa;">
                <table role="presentation" style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 40px 0; text-align: center;">
                            <table role="presentation" style="width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1); overflow: hidden;">
                                <!-- Header -->
                                <tr>
                                    <td style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px 30px; text-align: center;">
                                        <h1 style="color: #ffffff; margin: 0; font-size: 32px; font-weight: bold; letter-spacing: 1px;">
                                            FinTech Bank
                                        </h1>
                                        <p style="color: #e0e7ff; margin: 10px 0 0 0; font-size: 14px;">
                                            Tu banco digital de confianza
                                        </p>
                                    </td>
                                </tr>
                                
                                <!-- Content -->
                                <tr>
                                    <td style="padding: 40px 30px;">
                                        <h2 style="color: #1f2937; margin: 0 0 20px 0; font-size: 24px; font-weight: 600;">
                                            ¡Bienvenido, {user_name}!
                                        </h2>
                                        
                                        <p style="color: #4b5563; margin: 0 0 24px 0; font-size: 16px; line-height: 1.6;">
                                            Gracias por registrarte en <strong>FinTech Bank</strong>. Para completar tu registro y comenzar a disfrutar de nuestros servicios, necesitamos verificar tu correo electrónico.
                                        </p>
                                        
                                        <div style="background: linear-gradient(135deg, #e0e7ff 0%, #ede9fe 100%); border-radius: 12px; padding: 30px; text-align: center; margin: 30px 0;">
                                            <p style="color: #4b5563; margin: 0 0 15px 0; font-size: 14px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;">
                                                Tu código de verificación
                                            </p>
                                            <div style="background-color: #ffffff; border: 3px solid #667eea; border-radius: 8px; padding: 20px; display: inline-block;">
                                                <p style="color: #667eea; margin: 0; font-size: 32px; font-weight: bold; letter-spacing: 4px; font-family: 'Courier New', monospace;">
                                                    {verification_token}
                                                </p>
                                            </div>
                                            <p style="color: #6b7280; margin: 15px 0 0 0; font-size: 13px;">
                                                Copia este código y pégalo en la página de verificación
                                            </p>
                                        </div>
                                        
                                        <div style="background-color: #fef3c7; border-left: 4px solid #f59e0b; padding: 16px; border-radius: 6px; margin: 24px 0;">
                                            <p style="color: #92400e; margin: 0; font-size: 14px; line-height: 1.5;">
                                                <strong>⚠️ Importante:</strong> Este código expirará en <strong>24 horas</strong>. Si no solicitaste este registro, por favor ignora este correo.
                                            </p>
                                        </div>
                                        
                                        <div style="margin: 30px 0; padding: 20px; background-color: #f9fafb; border-radius: 8px;">
                                            <h3 style="color: #1f2937; margin: 0 0 15px 0; font-size: 16px; font-weight: 600;">
                                                🎯 ¿Qué puedes hacer con FinTech Bank?
                                            </h3>
                                            <ul style="color: #4b5563; margin: 0; padding-left: 20px; font-size: 14px; line-height: 1.8;">
                                                <li>Realizar transferencias seguras en tiempo real</li>
                                                <li>Monitorear todas tus transacciones</li>
                                                <li>Recibir notificaciones instantáneas</li>
                                                <li>Protección anti-fraude avanzada</li>
                                            </ul>
                                        </div>
                                    </td>
                                </tr>
                                
                                <!-- Footer -->
                                <tr>
                                    <td style="background-color: #f9fafb; padding: 30px; text-align: center; border-top: 1px solid #e5e7eb;">
                                        <p style="color: #6b7280; margin: 0 0 10px 0; font-size: 14px;">
                                            ¿Necesitas ayuda? Contáctanos en
                                        </p>
                                        <p style="margin: 0 0 20px 0;">
                                            <a href="mailto:{self.from_email}" style="color: #667eea; text-decoration: none; font-weight: 600; font-size: 14px;">
                                                {self.from_email}
                                            </a>
                                        </p>
                                        <p style="color: #9ca3af; margin: 0; font-size: 12px; line-height: 1.5;">
                                            © 2026 FinTech Bank. Todos los derechos reservados.<br>
                                            Este es un correo automático, por favor no respondas a este mensaje.
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </body>
            </html>
            """
            
            # Texto plano como fallback
            text_body = f"""
            FinTech Bank
            
            ¡Bienvenido, {user_name}!
            
            Gracias por registrarte en FinTech Bank. Para verificar tu cuenta, usa el siguiente código:
            
            CÓDIGO DE VERIFICACIÓN: {verification_token}
            
            Copia este código y pégalo en la página de verificación.
            
            Este código expirará en 24 horas.
            
            Si no solicitaste este registro, por favor ignora este correo.
            
            Saludos,
            Equipo de FinTech Bank
            """
            
            message.set_content(text_body)
            message.add_alternative(html_body, subtype='html')
            
            logger.info(f"Attempting to send verification email to {to_email}")
            
            await aiosmtplib.send(
                message,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_username or None,
                password=self.smtp_password or None,
                start_tls=self.use_tls
            )
            
            logger.info(f"Verification email sent successfully to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Error sending verification email to {to_email}: {str(e)}", exc_info=True)
            return False
    
    async def send_welcome_email(
        self,
        to_email: str,
        user_name: str
    ) -> bool:
        """
        Envía un correo de bienvenida al usuario tras verificar su cuenta
        
        Args:
            to_email: Email del destinatario
            user_name: Nombre del usuario
            
        Returns:
            True si se envió correctamente, False en caso contrario
        """
        try:
            message = EmailMessage()
            message["From"] = self.from_email
            message["To"] = to_email
            message["Subject"] = "¡Bienvenido a FinTech Bank! 🎉"
            
            # Plantilla HTML profesional de bienvenida
            html_body = f"""
            <!DOCTYPE html>
            <html lang="es">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>¡Bienvenido!</title>
            </head>
            <body style="margin: 0; padding: 0; font-family: 'Arial', sans-serif; background-color: #f4f7fa;">
                <table role="presentation" style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 40px 0; text-align: center;">
                            <table role="presentation" style="width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1); overflow: hidden;">
                                <!-- Header -->
                                <tr>
                                    <td style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); padding: 40px 30px; text-align: center;">
                                        <h1 style="color: #ffffff; margin: 0; font-size: 32px; font-weight: bold; letter-spacing: 1px;">
                                            FinTech Bank
                                        </h1>
                                        <p style="color: #d1fae5; margin: 10px 0 0 0; font-size: 14px;">
                                            ¡Tu cuenta está lista!
                                        </p>
                                    </td>
                                </tr>
                                
                                <!-- Content -->
                                <tr>
                                    <td style="padding: 40px 30px;">
                                        <div style="text-align: center; margin-bottom: 30px;">
                                            <div style="width: 80px; height: 80px; background: linear-gradient(135deg, #10b981 0%, #059669 100%); border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; margin-bottom: 20px;">
                                                <span style="font-size: 40px;">✓</span>
                                            </div>
                                        </div>
                                        
                                        <h2 style="color: #1f2937; margin: 0 0 20px 0; font-size: 28px; font-weight: 600; text-align: center;">
                                            ¡Bienvenido, {user_name}!
                                        </h2>
                                        
                                        <p style="color: #4b5563; margin: 0 0 24px 0; font-size: 16px; line-height: 1.6; text-align: center;">
                                            Tu cuenta ha sido <strong style="color: #10b981;">verificada exitosamente</strong>. Ya puedes disfrutar de todos los beneficios de FinTech Bank.
                                        </p>
                                        
                                        <div style="background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%); border-radius: 12px; padding: 30px; margin: 30px 0;">
                                            <h3 style="color: #065f46; margin: 0 0 20px 0; font-size: 18px; font-weight: 600; text-align: center;">
                                                🚀 Características Disponibles
                                            </h3>
                                            
                                            <table role="presentation" style="width: 100%;">
                                                <tr>
                                                    <td style="padding: 12px 0; vertical-align: top; width: 50%;">
                                                        <div style="display: flex; align-items: start;">
                                                            <span style="color: #10b981; font-size: 20px; margin-right: 10px;">💳</span>
                                                            <div>
                                                                <strong style="color: #065f46; font-size: 14px; display: block; margin-bottom: 4px;">Transferencias Seguras</strong>
                                                                <span style="color: #047857; font-size: 12px;">En tiempo real y con protección total</span>
                                                            </div>
                                                        </div>
                                                    </td>
                                                    <td style="padding: 12px 0; vertical-align: top; width: 50%;">
                                                        <div style="display: flex; align-items: start;">
                                                            <span style="color: #10b981; font-size: 20px; margin-right: 10px;">📊</span>
                                                            <div>
                                                                <strong style="color: #065f46; font-size: 14px; display: block; margin-bottom: 4px;">Dashboard Completo</strong>
                                                                <span style="color: #047857; font-size: 12px;">Visualiza toda tu actividad</span>
                                                            </div>
                                                        </div>
                                                    </td>
                                                </tr>
                                                <tr>
                                                    <td style="padding: 12px 0; vertical-align: top; width: 50%;">
                                                        <div style="display: flex; align-items: start;">
                                                            <span style="color: #10b981; font-size: 20px; margin-right: 10px;">🔔</span>
                                                            <div>
                                                                <strong style="color: #065f46; font-size: 14px; display: block; margin-bottom: 4px;">Notificaciones Instantáneas</strong>
                                                                <span style="color: #047857; font-size: 12px;">Mantente informado al instante</span>
                                                            </div>
                                                        </div>
                                                    </td>
                                                    <td style="padding: 12px 0; vertical-align: top; width: 50%;">
                                                        <div style="display: flex; align-items: start;">
                                                            <span style="color: #10b981; font-size: 20px; margin-right: 10px;">🛡️</span>
                                                            <div>
                                                                <strong style="color: #065f46; font-size: 14px; display: block; margin-bottom: 4px;">Anti-Fraude Avanzado</strong>
                                                                <span style="color: #047857; font-size: 12px;">Máxima seguridad en cada operación</span>
                                                            </div>
                                                        </div>
                                                    </td>
                                                </tr>
                                            </table>
                                        </div>
                                        
                                        <div style="text-align: center; margin: 30px 0;">
                                            <a href="http://localhost:3000" style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #ffffff; text-decoration: none; padding: 16px 40px; border-radius: 8px; font-weight: 600; font-size: 16px; box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);">
                                                Acceder a mi cuenta
                                            </a>
                                        </div>
                                        
                                        <div style="background-color: #f9fafb; border-radius: 8px; padding: 20px; margin: 24px 0;">
                                            <p style="color: #6b7280; margin: 0; font-size: 13px; line-height: 1.6; text-align: center;">
                                                💡 <strong>Consejo:</strong> Para mayor seguridad, nunca compartas tu contraseña con nadie y revisa regularmente tus transacciones.
                                            </p>
                                        </div>
                                    </td>
                                </tr>
                                
                                <!-- Footer -->
                                <tr>
                                    <td style="background-color: #f9fafb; padding: 30px; text-align: center; border-top: 1px solid #e5e7eb;">
                                        <p style="color: #6b7280; margin: 0 0 10px 0; font-size: 14px;">
                                            ¿Necesitas ayuda? Contáctanos en
                                        </p>
                                        <p style="margin: 0 0 20px 0;">
                                            <a href="mailto:{self.from_email}" style="color: #667eea; text-decoration: none; font-weight: 600; font-size: 14px;">
                                                {self.from_email}
                                            </a>
                                        </p>
                                        <p style="color: #9ca3af; margin: 0; font-size: 12px; line-height: 1.5;">
                                            © 2026 FinTech Bank. Todos los derechos reservados.<br>
                                            Este es un correo automático, por favor no respondas a este mensaje.
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </body>
            </html>
            """
            
            # Texto plano como fallback
            text_body = f"""
            FinTech Bank
            
            ¡Bienvenido, {user_name}!
            
            Tu cuenta ha sido verificada exitosamente. Ya puedes acceder a todas las funcionalidades de FinTech Bank.
            
            Características disponibles:
            - Transferencias seguras en tiempo real
            - Dashboard completo de actividad
            - Notificaciones instantáneas
            - Protección anti-fraude avanzada
            
            Accede a tu cuenta en: http://localhost:3000
            
            Saludos,
            Equipo de FinTech Bank
            """
            
            message.set_content(text_body)
            message.add_alternative(html_body, subtype='html')
            
            logger.info(f"Attempting to send welcome email to {to_email}")
            
            await aiosmtplib.send(
                message,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_username or None,
                password=self.smtp_password or None,
                start_tls=self.use_tls
            )
            
            logger.info(f"Welcome email sent successfully to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Error sending welcome email to {to_email}: {str(e)}", exc_info=True)
            return False


class TokenGenerator:
    """
    Generador de tokens seguros para verificación
    """
    
    @staticmethod
    def generate_verification_token() -> str:
        """Genera un código numérico de 6 dígitos"""
        return ''.join([str(secrets.randbelow(10)) for _ in range(6)])
