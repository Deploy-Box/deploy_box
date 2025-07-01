def get_base_email_template(content):
    """Base HTML email template with modern styling"""
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>DeployBox</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                margin: 0;
                padding: 0;
                background-color: #f8fafc;
            }}
            .email-container {{
                max-width: 600px;
                margin: 0 auto;
                background-color: #ffffff;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px 20px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 28px;
                font-weight: 600;
            }}
            .content {{
                padding: 40px 30px;
            }}
            .message {{
                background-color: #f8fafc;
                border-left: 4px solid #667eea;
                padding: 20px;
                margin: 20px 0;
                border-radius: 0 4px 4px 0;
            }}
            .button {{
                display: inline-block;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                text-decoration: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: 500;
                margin: 20px 0;
                text-align: center;
            }}
            .footer {{
                background-color: #f1f5f9;
                padding: 20px 30px;
                text-align: center;
                color: #64748b;
                font-size: 14px;
            }}
            .organization-name {{
                font-weight: 600;
                color: #667eea;
            }}
            .username {{
                font-weight: 600;
                color: #374151;
            }}
            @media only screen and (max-width: 600px) {{
                .email-container {{
                    margin: 10px;
                    border-radius: 4px;
                }}
                .content {{
                    padding: 20px 15px;
                }}
                .header {{
                    padding: 20px 15px;
                }}
                .header h1 {{
                    font-size: 24px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="email-container">
            <div class="header">
                <h1>🚀 DeployBox</h1>
            </div>
            <div class="content">
                {content}
            </div>
            <div class="footer">
                <p>© 2024 DeployBox. All rights reserved.</p>
                <p>This email was sent from DeployBox. If you have any questions, please contact our support team.</p>
            </div>
        </div>
    </body>
    </html>
    """

def get_invite_email_content(user, organization):
    """Generate content for organization invitation email"""
    return f"""
        <h2 style="color: #1f2937; margin-bottom: 20px;">Welcome to the Team! 🎉</h2>
        
        <p>Hello <span class="username">{user.username}</span>,</p>
        
        <div class="message">
            <p style="margin: 0; font-size: 16px;">
                You have been <strong>invited to join</strong> the organization 
                <span class="organization-name">{organization.name}</span> on DeployBox!
            </p>
        </div>
        
        <p>This means you now have access to:</p>
        <ul style="color: #4b5563; margin: 20px 0;">
            <li>Collaborate on projects with your team</li>
            <li>Deploy applications together</li>
            <li>Manage shared resources</li>
            <li>Access organization-wide settings</li>
        </ul>
        
        <p>We're excited to have you on board! If you have any questions about your new role, 
        don't hesitate to reach out to your organization administrator.</p>
        
        <p style="margin-top: 30px;">
            Best regards,<br>
            <strong>The DeployBox Team</strong>
        </p>
    """

def get_removed_email_content(user, organization):
    """Generate content for user removal email"""
    return f"""
        <h2 style="color: #1f2937; margin-bottom: 20px;">Organization Access Update</h2>
        
        <p>Hello <span class="username">{user.username}</span>,</p>
        
        <div class="message">
            <p style="margin: 0; font-size: 16px;">
                Your access to the organization 
                <span class="organization-name">{organization.name}</span> has been removed.
            </p>
        </div>
        
        <p>This means you no longer have access to:</p>
        <ul style="color: #4b5563; margin: 20px 0;">
            <li>Organization projects and resources</li>
            <li>Team collaboration features</li>
            <li>Shared deployments and settings</li>
        </ul>
        
        <p>If you believe this was done in error, please contact your organization administrator 
        or reach out to our support team.</p>
        
        <p style="margin-top: 30px;">
            Best regards,<br>
            <strong>The DeployBox Team</strong>
        </p>
    """

def get_left_email_content(user, organization):
    """Generate content for user leaving email"""
    return f"""
        <h2 style="color: #1f2937; margin-bottom: 20px;">Organization Departure Confirmation</h2>
        
        <p>Hello <span class="username">{user.username}</span>,</p>
        
        <div class="message">
            <p style="margin: 0; font-size: 16px;">
                You have successfully left the organization 
                <span class="organization-name">{organization.name}</span>.
            </p>
        </div>
        
        <p>Your departure has been processed and you no longer have access to:</p>
        <ul style="color: #4b5563; margin: 20px 0;">
            <li>Organization projects and resources</li>
            <li>Team collaboration features</li>
            <li>Shared deployments and settings</li>
        </ul>
        
        <p>Thank you for being part of the team! You can always rejoin if invited again in the future.</p>
        
        <p style="margin-top: 30px;">
            Best regards,<br>
            <strong>The DeployBox Team</strong>
        </p>
    """

def get_permission_update_email_content(user, organization):
    """Generate content for permission update email"""
    return f"""
        <h2 style="color: #1f2937; margin-bottom: 20px;">Permission Update Notification</h2>
        
        <p>Hello <span class="username">{user.username}</span>,</p>
        
        <div class="message">
            <p style="margin: 0; font-size: 16px;">
                Your permissions have been updated for the organization 
                <span class="organization-name">{organization.name}</span>.
            </p>
        </div>
        
        <p>This change may affect your ability to:</p>
        <ul style="color: #4b5563; margin: 20px 0;">
            <li>Access certain projects or resources</li>
            <li>Perform specific actions within the organization</li>
            <li>View or modify organization settings</li>
        </ul>
        
        <p>If you have any questions about your new permissions, please contact your organization administrator.</p>
        
        <p style="margin-top: 30px;">
            Best regards,<br>
            <strong>The DeployBox Team</strong>
        </p>
    """

def get_new_user_invite_email_content(user, organization, signup_url):
    """Generate content for new user invitation email"""
    return f"""
        <h2 style="color: #1f2937; margin-bottom: 20px;">You're Invited to Join DeployBox! 🚀</h2>
        
        <p>Hello there!</p>
        
        <div class="message">
            <p style="margin: 0; font-size: 16px;">
                <span class="username">{user.username}</span> has invited you to create an account and join their organization 
                <span class="organization-name">{organization.name}</span> on DeployBox!
            </p>
        </div>
        
        <p>DeployBox is a powerful platform for:</p>
        <ul style="color: #4b5563; margin: 20px 0;">
            <li>🚀 Deploying applications with ease</li>
            <li>👥 Collaborating with your team</li>
            <li>⚡ Managing infrastructure efficiently</li>
            <li>🔧 Streamlining your development workflow</li>
        </ul>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="{signup_url}" class="button" style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-decoration: none; padding: 12px 24px; border-radius: 6px; font-weight: 500;">
                Create Your Account
            </a>
        </div>
        
        <p>Once you create your account, you'll have immediate access to the organization and can start collaborating right away!</p>
        
        <p style="margin-top: 30px;">
            Best regards,<br>
            <strong>The DeployBox Team</strong>
        </p>
    """ 