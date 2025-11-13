import 'package:flutter/material.dart';

class DataPrivacyScreen extends StatelessWidget {
  const DataPrivacyScreen({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.grey[50],
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: Colors.black),
          onPressed: () => Navigator.pop(context),
        ),
        title: const Text(
          'Data and Privacy',
          style: TextStyle(
            color: Colors.black,
            fontWeight: FontWeight.w600,
            fontSize: 18,
          ),
        ),
        centerTitle: true,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header Section
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [Colors.blue[400]!, Colors.blue[600]!],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(16),
              ),
              child: Row(
                children: [
                  Icon(Icons.shield_outlined, color: Colors.white, size: 40),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: const [
                        Text(
                          'Privacy Policy',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 22,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        SizedBox(height: 4),
                        Text(
                          'Last Updated: November 2025',
                          style: TextStyle(
                            color: Colors.white70,
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),

            // Introduction
            _buildIntroCard(),
            const SizedBox(height: 16),

            // Information We Collect
            _buildSection(
              'Information We Collect',
              Icons.data_usage,
              [
                _buildSubSection('Personal Information', [
                  'Name for identification and personalized alerts',
                  'Email address for account verification',
                  'Encrypted password for security',
                  'Account role designation',
                ]),
                _buildSubSection('Health Data', [
                  'Heart Rate measurements',
                  'Blood Pressure readings',
                  'Body Temperature',
                  'Oxygen Saturation (SpO2)',
                  'Respiratory Rate',
                  'Timestamp for each measurement',
                ]),
                _buildSubSection('Location Data', [
                  'GPS coordinates during health alerts',
                  'Shared with emergency contacts',
                  'Collected only when app is active',
                ]),
                _buildSubSection('Device Information', [
                  'Device identifiers',
                  'Device names for your reference',
                  'FCM tokens for notifications',
                ]),
                _buildSubSection('Emergency Contact Info', [
                  'Contact names and phone numbers',
                  'Relationship types',
                  'For SMS alert delivery',
                ]),
              ],
            ),
            const SizedBox(height: 16),

            // How We Use Your Information
            _buildSection(
              'How We Use Your Information',
              Icons.insights,
              [
                _buildBulletPoint('Monitor vital signs against health thresholds'),
                _buildBulletPoint('Trigger alerts when thresholds are breached'),
                _buildBulletPoint('Send notifications to you and emergency contacts'),
                _buildBulletPoint('Provide location during emergencies'),
                _buildBulletPoint('Display health trends and historical data'),
                _buildBulletPoint('Manage your account and preferences'),
              ],
            ),
            const SizedBox(height: 16),

            // Data Storage and Security
            _buildSection(
              'Data Storage & Security',
              Icons.security,
              [
                _buildSubSection('Storage Location', [
                  'PostgreSQL on secure cloud infrastructure',
                  'SOC 2 Type II compliant data centers',
                  'Regular automated backups',
                ]),
                _buildSubSection('Security Measures', [
                  'Password encryption using bcrypt',
                  'TLS/SSL encrypted data transmission',
                  'JWT token authentication',
                  'Multi-factor authentication available',
                  'Firewall and intrusion detection',
                ]),
                _buildSubSection('Data Retention', [
                  'Active accounts: retained while active',
                  'Inactive accounts: 12 months then archived',
                  'Deleted accounts: permanently deleted within 30 days',
                ]),
              ],
            ),
            const SizedBox(height: 16),

            // Data Sharing
            _buildSection(
              'Data Sharing & Disclosure',
              Icons.people_outline,
              [
                _buildWarningCard(
                  'We NEVER sell your data',
                  'Your personal and health data will never be sold to third parties or used for advertising purposes.',
                ),
                const SizedBox(height: 12),
                _buildSubSection('We Share Data Only When:', [
                  'You explicitly authorize emergency contacts',
                  'You choose to share with healthcare providers',
                  'Required by law (court orders, subpoenas)',
                  'With service providers bound by contracts',
                ]),
                _buildSubSection('Service Providers:', [
                  'SMSPortal for text notifications',
                  'Firebase Cloud Messaging for app alerts',
                  'Render for cloud hosting',
                ]),
              ],
            ),
            const SizedBox(height: 16),

            // Your Privacy Rights
            _buildSection(
              'Your Privacy Rights',
              Icons.verified_user,
              [
                _buildSubSection('You Have the Right To:', [
                  'Access and view all your data',
                  'Download data in machine-readable format',
                  'Correct inaccurate information',
                  'Delete individual readings or entire account',
                  'Export data as CSV or JSON',
                  'Withdraw consent at any time',
                ]),
                _buildSubSection('Privacy Controls:', [
                  'Manage location and notification permissions',
                  'Configure personalized alert thresholds',
                  'Add or remove emergency contacts',
                  'Temporarily pause monitoring',
                ]),
              ],
            ),
            const SizedBox(height: 16),

            // Children's Privacy
            _buildInfoCard(
              'Children\'s Privacy',
              'MedGuardian is not intended for children under 18. We do not knowingly collect data from minors without parental consent.',
              Icons.child_care,
              Colors.orange,
            ),
            const SizedBox(height: 16),

            // Data Breach Notification
            _buildInfoCard(
              'Data Breach Notification',
              'In the unlikely event of a data breach, we will notify affected users within 72 hours and report to the Information Regulator as required by POPIA.',
              Icons.warning_amber,
              Colors.red,
            ),
            const SizedBox(height: 16),

            // Contact Information
            _buildContactCard(),
            const SizedBox(height: 24),

            // Acknowledgment
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.blue[50],
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.blue[200]!),
              ),
              child: Column(
                children: [
                  Icon(Icons.check_circle_outline, color: Colors.blue[600], size: 32),
                  const SizedBox(height: 12),
                  Text(
                    'By using MedGuardian, you acknowledge that you have read and understood this Privacy Policy and consent to the collection and use of your data as described.',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: 13,
                      color: Colors.blue[900],
                      height: 1.5,
                    ),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    'Your health data is yours. We are simply the custodians, committed to protecting it with the highest standards of security and privacy.',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: 12,
                      fontStyle: FontStyle.italic,
                      color: Colors.blue[700],
                      height: 1.4,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }

  Widget _buildIntroCard() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: Colors.grey.withOpacity(0.1),
            spreadRadius: 1,
            blurRadius: 4,
          ),
        ],
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.info_outline, color: Colors.blue[400], size: 24),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              'MedGuardian is committed to protecting your privacy and securing your personal health information. This policy explains how we collect, use, store, and protect your data.',
              style: TextStyle(
                fontSize: 14,
                color: Colors.grey[800],
                height: 1.5,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSection(String title, IconData icon, List<Widget> children) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: Colors.grey.withOpacity(0.1),
            spreadRadius: 1,
            blurRadius: 4,
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.blue[50],
              borderRadius: const BorderRadius.only(
                topLeft: Radius.circular(12),
                topRight: Radius.circular(12),
              ),
            ),
            child: Row(
              children: [
                Icon(icon, color: Colors.blue[600], size: 24),
                const SizedBox(width: 12),
                Text(
                  title,
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: Colors.blue[900],
                  ),
                ),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: children,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSubSection(String title, List<String> items) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: const TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w600,
            color: Colors.black87,
          ),
        ),
        const SizedBox(height: 8),
        ...items.map((item) => Padding(
          padding: const EdgeInsets.only(left: 16, bottom: 6),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('• ', style: TextStyle(color: Colors.blue[400], fontSize: 16)),
              Expanded(
                child: Text(
                  item,
                  style: TextStyle(fontSize: 14, color: Colors.grey[700], height: 1.4),
                ),
              ),
            ],
          ),
        )).toList(),
        const SizedBox(height: 12),
      ],
    );
  }

  Widget _buildBulletPoint(String text) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.check_circle, color: Colors.green[400], size: 20),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              text,
              style: TextStyle(fontSize: 14, color: Colors.grey[800], height: 1.4),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildWarningCard(String title, String description) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.green[50],
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.green[200]!),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.verified_user, color: Colors.green[600], size: 28),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: Colors.green[900],
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  description,
                  style: TextStyle(
                    fontSize: 13,
                    color: Colors.green[800],
                    height: 1.4,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInfoCard(String title, String description, IconData icon, Color color) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: color, size: 28),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: color.withOpacity(0.9),
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  description,
                  style: TextStyle(
                    fontSize: 13,
                    color: color.withOpacity(0.8),
                    height: 1.4,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildContactCard() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [Colors.blue[100]!, Colors.blue[50]!],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.blue[200]!),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.contact_support, color: Colors.blue[700], size: 28),
              const SizedBox(width: 12),
              Text(
                'Contact Us',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: Colors.blue[900],
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          _buildContactItem(Icons.email, 'Privacy Inquiries', 'privacy@medguardian.app'),
          _buildContactItem(Icons.security, 'Data Protection', 'dpo@medguardian.app'),
          _buildContactItem(Icons.support, 'General Support', 'support@medguardian.app'),
          const SizedBox(height: 8),
          Text(
            'Response Time: We aim to respond within 5 business days',
            style: TextStyle(
              fontSize: 12,
              color: Colors.blue[700],
              fontStyle: FontStyle.italic,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildContactItem(IconData icon, String label, String email) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Icon(icon, color: Colors.blue[600], size: 18),
          const SizedBox(width: 8),
          Text(
            '$label: ',
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w600,
              color: Colors.blue[900],
            ),
          ),
          Expanded(
            child: Text(
              email,
              style: TextStyle(
                fontSize: 13,
                color: Colors.blue[800],
              ),
            ),
          ),
        ],
      ),
    );
  }
}