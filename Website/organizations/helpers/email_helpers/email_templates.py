from django.conf import settings

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
                <p>© 2025 DeployBox. All rights reserved.</p>
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

def get_project_transfer_invitation_content(transfer_invitation, accept_url):
    """Generate content for project transfer invitation email"""
    return f"""
        <h2 style="color: #1f2937; margin-bottom: 20px;">Project Ownership Transfer 🎯</h2>
        
        <p>Hello {transfer_invitation.to_name},</p>
        
        <div class="message">
            <p style="margin: 0; font-size: 16px;">
                Your developer has built a project on DeployBox and is ready to transfer ownership to you!
            </p>
        </div>
        
        <p><strong>Project Details:</strong></p>
        <ul style="color: #4b5563; margin: 20px 0;">
            <li><strong>Project Name:</strong> {transfer_invitation.project.name}</li>
            <li><strong>Description:</strong> {transfer_invitation.project.description}</li>
            <li><strong>Developer:</strong> {transfer_invitation.from_organization.name}</li>
            {f'<li><strong>Your Company:</strong> {transfer_invitation.to_company}</li>' if transfer_invitation.to_company else ''}
        </ul>
        
        <p><strong>What happens when you accept:</strong></p>
        <ul style="color: #4b5563; margin: 20px 0;">
            <li>✅ Project ownership transfers to your account</li>
            <li>✅ Billing responsibility moves to you</li>
            <li>✅ Full control over the project and infrastructure</li>
            <li>✅ Developer can remain as collaborator (if you choose)</li>
        </ul>
        
        <p>This invitation expires in 7 days. Click below to accept and take ownership!</p>
        
        <a href="{accept_url}" class="button" style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-decoration: none; padding: 12px 24px; border-radius: 6px; font-weight: 500;">
            Accept & Take Ownership
        </a>
        
        <p style="margin-top: 30px;">
            Best regards,<br>
            <strong>The DeployBox Team</strong>
        </p>
    """

def get_project_transfer_accepted_content(transfer_invitation):
    """Generate content for project transfer acceptance confirmation"""
    return f"""
        <h2 style="color: #1f2937; margin-bottom: 20px;">Project Transfer Complete! ✅</h2>
        
        <p>Hello {transfer_invitation.to_name},</p>
        
        <div class="message">
            <p style="margin: 0; font-size: 16px;">
                Congratulations! You have successfully taken ownership of the project 
                <span class="organization-name">{transfer_invitation.project.name}</span>.
            </p>
        </div>
        
        <p><strong>What's been transferred:</strong></p>
        <ul style="color: #4b5563; margin: 20px 0;">
            <li>✅ Project ownership and control</li>
            <li>✅ Billing responsibility</li>
            <li>✅ Infrastructure management</li>
            <li>✅ All project resources and settings</li>
        </ul>
        
        <p><strong>Next steps:</strong></p>
        <ul style="color: #4b5563; margin: 20px 0;">
            <li>Set up your payment method in the dashboard</li>
            <li>Review your project settings and configuration</li>
            <li>Configure any additional team members if needed</li>
            <li>Monitor your usage and billing</li>
        </ul>
        
        <p>You can now access your project from your DeployBox dashboard.</p>
        
        <p style="margin-top: 30px;">
            Best regards,<br>
            <strong>The DeployBox Team</strong>
        </p>
    """

def get_project_transfer_notification_content(transfer_invitation):
    """Email content for notifying the original developer about transfer completion"""
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
            <h1 style="margin: 0; font-size: 24px;">Project Transfer Completed</h1>
            <p style="margin: 10px 0 0 0; opacity: 0.9;">Your project has been successfully transferred</p>
        </div>
        
        <div style="background: white; padding: 30px; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 10px 10px;">
            <h2 style="color: #374151; margin-top: 0;">Transfer Details</h2>
            
            <div style="background: #f9fafb; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="color: #10b981; margin-top: 0;">Project Information</h3>
                <ul style="list-style: none; padding: 0; margin: 0;">
                    <li style="margin-bottom: 10px;"><strong>Project Name:</strong> {transfer_invitation.project.name}</li>
                    <li style="margin-bottom: 10px;"><strong>Description:</strong> {transfer_invitation.project.description}</li>
                    <li style="margin-bottom: 10px;"><strong>New Owner:</strong> {transfer_invitation.to_name} ({transfer_invitation.to_email})</li>
                    <li style="margin-bottom: 10px;"><strong>Transfer Date:</strong> {transfer_invitation.accepted_at.strftime('%B %d, %Y at %I:%M %p')}</li>
                </ul>
            </div>
            
            <div style="background: #ecfdf5; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #10b981;">
                <h3 style="color: #065f46; margin-top: 0;">What Happened</h3>
                <ul style="color: #065f46;">
                    <li>Project ownership has been transferred to {transfer_invitation.to_name}</li>
                    <li>Billing responsibility has moved to the new owner</li>
                    <li>Infrastructure control has been transferred</li>
                    <li>You {'will remain as a collaborator' if transfer_invitation.keep_developer else 'no longer have access to the project'}</li>
                </ul>
            </div>
            
            <div style="text-align: center; margin-top: 30px;">
                <a href="https://deploybox.com/dashboard/" style="background: #10b981; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; display: inline-block; font-weight: bold;">
                    View Your Dashboard
                </a>
            </div>
            
            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; color: #6b7280; font-size: 14px;">
                <p>If you have any questions about this transfer, please contact our support team.</p>
                <p>Thank you for using DeployBox!</p>
            </div>
        </div>
    </div>
    """

def get_project_transfer_with_signup_invitation_content(transfer_invitation, pending_invite):
    """Email content for project transfer invitation that includes signup for new users"""
    signup_url = f"{settings.HOST}/signup/?invite_id={pending_invite.id}&transfer_id={transfer_invitation.id}"
    
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
            <h1 style="margin: 0; font-size: 24px;">🎉 Your Project is Ready!</h1>
            <p style="margin: 10px 0 0 0; opacity: 0.9;">Your developer has completed your project and is ready to transfer ownership to you</p>
        </div>
        
        <div style="background: white; padding: 30px; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 10px 10px;">
            <h2 style="color: #374151; margin-top: 0;">Project Transfer Invitation</h2>
            
            <div style="background: #fef3c7; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #f59e0b;">
                <h3 style="color: #92400e; margin-top: 0;">🚀 Get Started in 2 Steps</h3>
                <ol style="color: #92400e; line-height: 1.6;">
                    <li><strong>Create your DeployBox account</strong> (takes 2 minutes)</li>
                    <li><strong>Accept project ownership</strong> and start managing your infrastructure</li>
                </ol>
            </div>
            
            <div style="background: #f9fafb; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="color: #10b981; margin-top: 0;">Project Details</h3>
                <ul style="list-style: none; padding: 0; margin: 0;">
                    <li style="margin-bottom: 10px;"><strong>Project Name:</strong> {transfer_invitation.project.name}</li>
                    <li style="margin-bottom: 10px;"><strong>Description:</strong> {transfer_invitation.project.description}</li>
                    <li style="margin-bottom: 10px;"><strong>Developer:</strong> {transfer_invitation.from_organization.name}</li>
                    {f'<li style="margin-bottom: 10px;"><strong>Your Company:</strong> {transfer_invitation.to_company}</li>' if transfer_invitation.to_company else ''}
                </ul>
            </div>
            
            <div style="background: #ecfdf5; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #10b981;">
                <h3 style="color: #065f46; margin-top: 0;">What You'll Get</h3>
                <ul style="color: #065f46;">
                    <li>✅ Full ownership of your project</li>
                    <li>✅ Complete control over infrastructure</li>
                    <li>✅ Billing management</li>
                    <li>✅ Developer support {'(optional)' if transfer_invitation.keep_developer else ''}</li>
                    <li>✅ Professional hosting and deployment</li>
                </ul>
            </div>
            
            <div style="background: #fef2f2; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #ef4444;">
                <h3 style="color: #991b1b; margin-top: 0;">⏰ Important</h3>
                <p style="color: #991b1b; margin: 0;">This invitation expires on <strong>{transfer_invitation.expires_at.strftime('%B %d, %Y')}</strong>. Please accept it before then.</p>
            </div>
            
            <div style="text-align: center; margin-top: 30px;">
                <a href="{signup_url}" style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; padding: 15px 40px; text-decoration: none; border-radius: 8px; display: inline-block; font-weight: bold; font-size: 16px; box-shadow: 0 4px 6px rgba(16, 185, 129, 0.25);">
                    🚀 Create Account & Accept Project
                </a>
            </div>
            
            <div style="margin-top: 20px; text-align: center;">
                <p style="color: #6b7280; font-size: 14px; margin: 0;">
                    This link will create your account and automatically accept the project transfer
                </p>
            </div>
            
            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; color: #6b7280; font-size: 14px;">
                <p>If you have any questions, please contact your developer or our support team.</p>
                <p>Welcome to DeployBox! 🎉</p>
            </div>
        </div>
    </div>
    """ 