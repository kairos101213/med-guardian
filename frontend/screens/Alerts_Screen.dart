import 'package:flutter/material.dart';
import 'package:flutter_application_1/services/auth_service.dart';
import 'package:intl/intl.dart';

class AlertsScreen extends StatefulWidget {
  const AlertsScreen({Key? key}) : super(key: key);

  @override
  State<AlertsScreen> createState() => _AlertsScreenState();
}

class _AlertsScreenState extends State<AlertsScreen> {
  final AuthService _authService = AuthService();
  
  List<EmergencyAlert> _allAlerts = [];
  List<EmergencyAlert> _displayedAlerts = [];
  bool _isLoading = false;
  String? _errorMessage;
  bool _showOnlyUnresolved = true; // Default filter

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) {
        _loadAlerts();
      }
    });
  }

  Future<void> _loadAlerts() async {
    if (!mounted) return;
    
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });
    
    try {
      final result = await _authService.getEmergencies();
      
      if (!mounted) return;
      
      if (result['success'] == true && result['data'] != null) {
        final alertsList = <EmergencyAlert>[];
        
        for (var json in (result['data'] as List)) {
          try {
            alertsList.add(EmergencyAlert.fromJson(json as Map<String, dynamic>));
          } catch (e) {
            print('❌ Error parsing alert: $e');
            print('   JSON: $json');
          }
        }
        
        // Sort by timestamp (newest first)
        alertsList.sort((a, b) => b.timestamp.compareTo(a.timestamp));
        
        if (mounted) {
          setState(() {
            _allAlerts = alertsList;
            _applyFilter();
          });
        }
      } else {
        if (mounted) {
          setState(() {
            _errorMessage = result['error']?.toString() ?? 'Failed to load alerts';
          });
        }
      }
    } catch (e) {
      print('❌ Error loading alerts: $e');
      if (mounted) {
        setState(() {
          _errorMessage = 'Failed to load alerts: $e';
        });
      }
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  void _applyFilter() {
    setState(() {
      if (_showOnlyUnresolved) {
        _displayedAlerts = _allAlerts.where((a) => !a.resolved).toList();
      } else {
        _displayedAlerts = List.from(_allAlerts);
      }
    });
  }

  void _toggleFilter() {
    setState(() {
      _showOnlyUnresolved = !_showOnlyUnresolved;
      _applyFilter();
    });
  }

  Future<void> _markAsResolved(EmergencyAlert alert) async {
    try {
      final result = await _authService.updateEmergency(alert.id, resolved: true);
      
      if (result['success'] == true) {
        if (mounted) {
          setState(() {
            // Update in _allAlerts
            final index = _allAlerts.indexWhere((a) => a.id == alert.id);
            if (index != -1) {
              _allAlerts[index] = EmergencyAlert(
                id: alert.id,
                userId: alert.userId,
                deviceId: alert.deviceId,
                emergencyType: alert.emergencyType,
                severity: alert.severity,
                description: alert.description,
                timestamp: alert.timestamp,
                resolved: true,
              );
            }
            
            // Reapply filter
            _applyFilter();
          });
          
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('✅ Alert marked as resolved'),
              backgroundColor: Colors.green,
              duration: Duration(seconds: 2),
            ),
          );
        }
      } else {
        throw Exception(result['error'] ?? 'Failed to resolve alert');
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('❌ Failed to resolve alert: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  void _showHelpDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Row(
          children: [
            Icon(Icons.help_outline, color: Colors.blue[700], size: 28),
            const SizedBox(width: 8),
            const Text('Help & Support'),
          ],
        ),
        content: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text(
                'Alert Notifications',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 12),
              const Text(
                'View and manage all your health alerts and emergency notifications in one place.',
                style: TextStyle(fontSize: 14),
              ),
              const SizedBox(height: 16),
              _buildHelpSection(
                icon: Icons.notification_important_outlined,
                title: 'Alert Types',
                description:
                    'Alerts are triggered by threshold breaches (heart rate, blood pressure, oxygen levels, temperature) or SOS activations (manual or automatic).',
              ),
              const SizedBox(height: 12),
              _buildHelpSection(
                icon: Icons.filter_alt,
                title: 'Filter Button',
                description:
                    'Toggle the filter to show only unresolved alerts (purple icon) or view all alerts including resolved ones (grey icon). By default, only unresolved alerts are shown.',
              ),
              const SizedBox(height: 12),
              _buildHelpSection(
                icon: Icons.circle,
                title: 'Unresolved Indicator',
                description:
                    'A red dot appears on the right side of unresolved alerts. Once marked as resolved, the dot disappears.',
              ),
              const SizedBox(height: 12),
              _buildHelpSection(
                icon: Icons.touch_app,
                title: 'Alert Details',
                description:
                    'Tap any alert to view full details including description, timestamp, and severity. You can mark unresolved alerts as resolved from the detail view.',
              ),
              const SizedBox(height: 12),
              _buildHelpSection(
                icon: Icons.label_important,
                title: 'Severity Levels',
                description:
                    'Alerts are color-coded by severity: Red (Critical/High), Orange (Medium/Moderate), Yellow (Low). Higher severity alerts require immediate attention.',
              ),
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.blue[50],
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.blue[200]!),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(Icons.info_outline, color: Colors.blue[900], size: 20),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Tip: Pull down to refresh your alerts list. Emergency contacts are automatically notified when alerts are triggered.',
                        style: TextStyle(
                          fontSize: 12,
                          color: Colors.blue[900],
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }

  Widget _buildHelpSection({
    required IconData icon,
    required String title,
    required String description,
  }) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, color: Colors.blue[700], size: 24),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: const TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                description,
                style: const TextStyle(
                  fontSize: 13,
                  height: 1.4,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.grey[50],
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        title: const Text(
          'Alert Notifications',
          style: TextStyle(
            color: Colors.black,
            fontSize: 18,
            fontWeight: FontWeight.w600,
          ),
        ),
        centerTitle: true,
        actions: [
          // Filter toggle
          IconButton(
            onPressed: _toggleFilter,
            icon: Container(
              width: 32,
              height: 32,
              decoration: BoxDecoration(
                color: _showOnlyUnresolved ? const Color(0xFF7C3AED) : Colors.grey[300],
                shape: BoxShape.circle,
              ),
              child: Icon(
                _showOnlyUnresolved ? Icons.filter_alt : Icons.filter_alt_off,
                color: _showOnlyUnresolved ? Colors.white : Colors.grey,
                size: 18,
              ),
            ),
          ),
          // Help button
          IconButton(
            onPressed: _showHelpDialog,
            icon: Container(
              width: 32,
              height: 32,
              decoration: BoxDecoration(
                color: Colors.grey[300],
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.help_outline,
                color: Colors.grey,
                size: 18,
              ),
            ),
          ),
        ],
      ),
      body: SafeArea(
        child: _buildBody(),
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(
        child: CircularProgressIndicator(
          valueColor: AlwaysStoppedAnimation<Color>(Color(0xFF7C3AED)),
        ),
      );
    }
    
    if (_errorMessage != null) {
      return _buildErrorState();
    }
    
    if (_displayedAlerts.isEmpty) {
      return _buildEmptyState();
    }
    
    return RefreshIndicator(
      onRefresh: _loadAlerts,
      color: const Color(0xFF7C3AED),
      child: _buildAlertsList(),
    );
  }

  Widget _buildErrorState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.error_outline,
              size: 64,
              color: Colors.red[400],
            ),
            const SizedBox(height: 16),
            Text(
              'Error Loading Alerts',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.w600,
                color: Colors.grey[800],
              ),
            ),
            const SizedBox(height: 8),
            Text(
              _errorMessage ?? 'Unknown error',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 14,
                color: Colors.grey[600],
              ),
            ),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: _loadAlerts,
              icon: const Icon(Icons.refresh, color: Colors.white),
              label: const Text('Retry', style: TextStyle(color: Colors.white)),
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF7C3AED),
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildAlertsList() {
    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: _displayedAlerts.length,
      itemBuilder: (context, index) {
        return Padding(
          padding: EdgeInsets.only(bottom: index == _displayedAlerts.length - 1 ? 100 : 12),
          child: _buildAlertCard(_displayedAlerts[index]),
        );
      },
    );
  }

  Widget _buildAlertCard(EmergencyAlert alert) {
    final alertConfig = _getAlertConfig(alert.emergencyType);
    final severityColor = _getSeverityColor(alert.severity);
    final formattedType = _formatAlertType(alert.emergencyType);
    
    return GestureDetector(
      onTap: () => _showAlertDetails(alert),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(12),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.05),
              blurRadius: 8,
              offset: const Offset(0, 2),
            ),
          ],
          border: Border.all(
            color: alertConfig.backgroundColor.withOpacity(0.3),
            width: 1,
          ),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Icon
            Container(
              width: 48,
              height: 48,
              decoration: BoxDecoration(
                color: alertConfig.backgroundColor,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(
                alertConfig.icon,
                color: alertConfig.iconColor,
                size: 24,
              ),
            ),
            const SizedBox(width: 12),
            // Content
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              formattedType.title,
                              style: const TextStyle(
                                fontSize: 15,
                                fontWeight: FontWeight.w600,
                                color: Colors.black,
                                height: 1.2,
                              ),
                            ),
                            if (formattedType.subtitle != null) ...[
                              const SizedBox(height: 2),
                              Text(
                                formattedType.subtitle!,
                                style: TextStyle(
                                  fontSize: 13,
                                  fontWeight: FontWeight.w500,
                                  color: Colors.grey[700],
                                  height: 1.2,
                                ),
                              ),
                            ],
                          ],
                        ),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        _formatTimeAgo(alert.timestamp),
                        style: TextStyle(
                          fontSize: 11,
                          color: Colors.grey[600],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  // Severity badge
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: severityColor.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: severityColor.withOpacity(0.3)),
                    ),
                    child: Text(
                      alert.severity.toUpperCase(),
                      style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w700,
                        color: severityColor,
                        letterSpacing: 0.5,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            // Unresolved indicator
            if (!alert.resolved)
              Container(
                width: 12,
                height: 12,
                margin: const EdgeInsets.only(left: 8, top: 2),
                decoration: const BoxDecoration(
                  color: Colors.red,
                  shape: BoxShape.circle,
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.notifications_none,
            size: 64,
            color: Colors.grey[400],
          ),
          const SizedBox(height: 16),
          Text(
            _showOnlyUnresolved ? 'No Unresolved Alerts' : 'No Alerts',
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.w600,
              color: Colors.grey[600],
            ),
          ),
          const SizedBox(height: 8),
          Text(
            _showOnlyUnresolved 
                ? 'All alerts have been resolved!' 
                : 'You\'re all caught up!',
            style: TextStyle(
              fontSize: 14,
              color: Colors.grey[500],
            ),
          ),
        ],
      ),
    );
  }

  void _showAlertDetails(EmergencyAlert alert) {
    final alertConfig = _getAlertConfig(alert.emergencyType);
    final formattedType = _formatAlertType(alert.emergencyType);
    
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => Container(
        padding: const EdgeInsets.all(24),
        decoration: const BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 48,
                  height: 48,
                  decoration: BoxDecoration(
                    color: alertConfig.backgroundColor,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Icon(
                    alertConfig.icon,
                    color: alertConfig.iconColor,
                    size: 24,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        formattedType.title,
                        style: const TextStyle(
                          fontSize: 17,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      if (formattedType.subtitle != null)
                        Text(
                          formattedType.subtitle!,
                          style: TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w500,
                            color: Colors.grey[700],
                          ),
                        ),
                      const SizedBox(height: 2),
                      Text(
                        DateFormat('MMM dd, yyyy • HH:mm').format(alert.timestamp),
                        style: TextStyle(
                          fontSize: 13,
                          color: Colors.grey[600],
                        ),
                      ),
                    ],
                  ),
                ),
                if (!alert.resolved)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: Colors.red[50],
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: Colors.red[200]!),
                    ),
                    child: Text(
                      'UNRESOLVED',
                      style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w700,
                        color: Colors.red[700],
                        letterSpacing: 0.5,
                      ),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 16),
            const Text(
              'Description',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w600,
                color: Colors.grey,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              alert.description,
              style: const TextStyle(
                fontSize: 16,
                height: 1.4,
              ),
            ),
            const SizedBox(height: 24),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: () => Navigator.pop(context),
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                    ),
                    child: const Text('Cancel'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton(
                    onPressed: alert.resolved
                        ? null
                        : () {
                            Navigator.pop(context);
                            _markAsResolved(alert);
                          },
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.green,
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                    ),
                    child: Text(
                      alert.resolved ? 'Resolved' : 'Mark Resolved',
                      style: const TextStyle(color: Colors.white),
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  FormattedAlertType _formatAlertType(String emergencyType) {
    // Remove underscores and convert to title case
    final cleaned = emergencyType.replaceAll('_', ' ');
    
    // Handle specific cases with better formatting
    if (cleaned.toLowerCase().contains('threshold breach')) {
      // Extract the metric after "threshold breach:"
      final parts = cleaned.split(':');
      if (parts.length > 1) {
        final metric = _toTitleCase(parts[1].trim());
        return FormattedAlertType(
          title: 'Threshold Breach:',
          subtitle: metric,
        );
      }
      return FormattedAlertType(title: 'Threshold Breach');
    }
    
    if (cleaned.toLowerCase().contains('sos')) {
      if (cleaned.toLowerCase().contains('manual')) {
        return FormattedAlertType(title: 'SOS: Manual');
      }
      if (cleaned.toLowerCase().contains('automatic')) {
        return FormattedAlertType(title: 'SOS: Automatic');
      }
      return FormattedAlertType(title: 'SOS Alert');
    }
    
    // Default: convert to title case
    return FormattedAlertType(title: _toTitleCase(cleaned));
  }

  String _toTitleCase(String text) {
    return text
        .split(' ')
        .map((word) => word.isEmpty 
            ? '' 
            : word[0].toUpperCase() + word.substring(1).toLowerCase())
        .join(' ');
  }

  AlertConfig _getAlertConfig(String emergencyType) {
    final type = emergencyType.toLowerCase();
    
    if (type.contains('sos') || type.contains('emergency')) {
      return AlertConfig(
        icon: Icons.sos,
        iconColor: Colors.red,
        backgroundColor: const Color(0xFFFFEBEE),
      );
    } else if (type.contains('heart') || type.contains('cardiac')) {
      return AlertConfig(
        icon: Icons.favorite,
        iconColor: Colors.red,
        backgroundColor: const Color(0xFFFFEBEE),
      );
    } else if (type.contains('fall')) {
      return AlertConfig(
        icon: Icons.person_off,
        iconColor: Colors.orange,
        backgroundColor: const Color(0xFFFFF3E0),
      );
    } else if (type.contains('blood pressure') || type.contains('bp') || type.contains('systolic') || type.contains('diastolic')) {
      return AlertConfig(
        icon: Icons.monitor_heart,
        iconColor: Colors.purple,
        backgroundColor: const Color(0xFFF3E5F5),
      );
    } else if (type.contains('oxygen') || type.contains('spo2') || type.contains('saturation')) {
      return AlertConfig(
        icon: Icons.water_drop,
        iconColor: Colors.blue,
        backgroundColor: const Color(0xFFE3F2FD),
      );
    } else if (type.contains('temperature')) {
      return AlertConfig(
        icon: Icons.thermostat,
        iconColor: Colors.orange,
        backgroundColor: const Color(0xFFFFF3E0),
      );
    } else {
      return AlertConfig(
        icon: Icons.warning,
        iconColor: Colors.amber,
        backgroundColor: const Color(0xFFFFF8E1),
      );
    }
  }

  Color _getSeverityColor(String severity) {
    switch (severity.toLowerCase()) {
      case 'critical':
      case 'high':
        return Colors.red;
      case 'medium':
      case 'moderate':
        return Colors.orange;
      case 'low':
        return Colors.yellow[700]!;
      default:
        return Colors.grey;
    }
  }

  String _formatTimeAgo(DateTime timestamp) {
    final now = DateTime.now();
    final difference = now.difference(timestamp);

    if (difference.inMinutes < 1) {
      return 'Just now';
    } else if (difference.inMinutes < 60) {
      return '${difference.inMinutes}m ago';
    } else if (difference.inHours < 24) {
      return '${difference.inHours}h ago';
    } else if (difference.inDays < 7) {
      return '${difference.inDays}d ago';
    } else {
      return DateFormat('MMM dd').format(timestamp);
    }
  }
}

class FormattedAlertType {
  final String title;
  final String? subtitle;

  FormattedAlertType({required this.title, this.subtitle});
}

class AlertConfig {
  final IconData icon;
  final Color iconColor;
  final Color backgroundColor;

  AlertConfig({
    required this.icon,
    required this.iconColor,
    required this.backgroundColor,
  });
}

class EmergencyAlert {
  final int id;
  final int userId;
  final int? deviceId;
  final String emergencyType;
  final String severity;
  final String description;
  final DateTime timestamp;
  final bool resolved;

  EmergencyAlert({
    required this.id,
    required this.userId,
    this.deviceId,
    required this.emergencyType,
    required this.severity,
    required this.description,
    required this.timestamp,
    required this.resolved,
  });

  factory EmergencyAlert.fromJson(Map<String, dynamic> json) {
    return EmergencyAlert(
      id: json['id'] as int,
      userId: json['user_id'] as int,
      deviceId: json['device_id'] as int?,
      emergencyType: json['emergency_type'] as String? ?? 'Unknown',
      severity: json['severity'] as String? ?? 'medium',
      description: json['description'] as String? ?? 'No description available',
      timestamp: DateTime.parse(json['timestamp'] as String),
      resolved: json['resolved'] as bool? ?? false,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'user_id': userId,
      'device_id': deviceId,
      'emergency_type': emergencyType,
      'severity': severity,
      'description': description,
      'timestamp': timestamp.toIso8601String(),
      'resolved': resolved,
    };
  }
}