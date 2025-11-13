import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../services/auth_service.dart';

class ContactsScreen extends StatefulWidget {
  const ContactsScreen({Key? key}) : super(key: key);

  @override
  State<ContactsScreen> createState() => _ContactsScreenState();
}

class _ContactsScreenState extends State<ContactsScreen> {
  final AuthService _authService = AuthService();
  List<EmergencyContact> _contacts = [];

  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _phoneController = TextEditingController();
  final TextEditingController _customRelationController = TextEditingController();

  final _formKey = GlobalKey<FormState>();
  bool _loading = false;

  // Relation dropdown
  String? _selectedRelation;
  String _phoneError = '';
  
  final List<String> _relationOptions = [
    'Father',
    'Mother',
    'Sister',
    'Brother',
    'Grandmother',
    'Grandfather',
    'Aunt',
    'Uncle',
    'Daughter',
    'Son',
    'Friend',
    'Custom',
  ];

  @override
  void initState() {
    super.initState();
    _fetchContacts();
  }

  @override
  void dispose() {
    _nameController.dispose();
    _phoneController.dispose();
    _customRelationController.dispose();
    super.dispose();
  }

  // ===== API CALLS =====

  Future<void> _fetchContacts() async {
    setState(() => _loading = true);
    try {
      final contacts = await _authService.getEmergencyContacts();
      setState(() {
        _contacts = contacts;
      });
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text("Failed to fetch contacts: $e"),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  Future<void> _addContact() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;

    // Validate relation
    if (_selectedRelation == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text("Please select a relation type"),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    if (_selectedRelation == 'Custom' && _customRelationController.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text("Please enter a custom relation"),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    setState(() => _loading = true);
    try {
      final phoneNumber = '+27${_phoneController.text.trim()}';
      final relation = _selectedRelation == 'Custom'
          ? _customRelationController.text.trim()
          : _selectedRelation!;

      final result = await _authService.addEmergencyContact(
        _nameController.text.trim(),
        phoneNumber,
        relation: relation,
      );

      if (mounted) {
        if (result['success'] == true) {
          _nameController.clear();
          _phoneController.clear();
          _customRelationController.clear();
          _selectedRelation = null;
          Navigator.of(context).pop();
          
          await _fetchContacts(); // refresh list
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(result['error'] ?? "Failed to add contact"),
              backgroundColor: Colors.red,
            ),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text("Error adding contact: $e"),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  Future<void> _updateContact(EmergencyContact contact) async {
    if (!(_formKey.currentState?.validate() ?? false)) return;

    // Validate relation
    if (_selectedRelation == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text("Please select a relation type"),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    if (_selectedRelation == 'Custom' && _customRelationController.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text("Please enter a custom relation"),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    setState(() => _loading = true);
    try {
      final phoneNumber = '+27${_phoneController.text.trim()}';
      final relation = _selectedRelation == 'Custom'
          ? _customRelationController.text.trim()
          : _selectedRelation!;

      final result = await _authService.updateEmergencyContact(
        contact.id,
        _nameController.text.trim(),
        phoneNumber,
        relation: relation,
      );

      if (mounted) {
        if (result['success'] == true) {
          _nameController.clear();
          _phoneController.clear();
          _customRelationController.clear();
          _selectedRelation = null;
          Navigator.of(context).pop();
          
          await _fetchContacts(); // refresh list
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(result['error'] ?? "Failed to update contact"),
              backgroundColor: Colors.red,
            ),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text("Error updating contact: $e"),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  Future<void> _deleteContact(int contactId) async {
    setState(() => _loading = true);
    try {
      final result = await _authService.deleteEmergencyContact(contactId);

      if (mounted) {
        if (result['success'] == true) {
          await _fetchContacts(); // refresh list
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(result['error'] ?? "Failed to delete contact"),
              backgroundColor: Colors.red,
            ),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text("Error deleting contact: $e"),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  // ===== UI =====

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
                'Emergency Contacts',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 12),
              const Text(
                'This page allows you to manage your emergency contacts who will be notified in critical situations.',
                style: TextStyle(fontSize: 14),
              ),
              const SizedBox(height: 16),
              _buildHelpSection(
                icon: Icons.warning_amber_rounded,
                title: 'SOS Alerts',
                description:
                    'When you trigger an SOS alert, all your emergency contacts will receive an SMS notification with your current location and a distress message.',
              ),
              const SizedBox(height: 12),
              _buildHelpSection(
                icon: Icons.monitor_heart_outlined,
                title: 'Vital Signs Breach',
                description:
                    'If your health vitals (heart rate, blood pressure, oxygen levels, or temperature) breach their safety thresholds, your emergency contacts will be automatically notified via SMS.',
              ),
              const SizedBox(height: 12),
              _buildHelpSection(
                icon: Icons.phone_android,
                title: 'Phone Number Format',
                description:
                    'Enter only the 9 digits after the area code. The system automatically adds +27 for South African numbers (e.g., enter 838555008 for +27838555008).',
              ),
              const SizedBox(height: 12),
              _buildHelpSection(
                icon: Icons.people_outline,
                title: 'Contact Management',
                description:
                    'Add, edit, or delete contacts as needed. We recommend adding at least 2-3 trusted contacts for maximum safety.',
              ),
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.amber[50],
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.amber[200]!),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(Icons.info_outline, color: Colors.amber[900], size: 20),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Important: Ensure all contacts have consented to receiving emergency notifications.',
                        style: TextStyle(
                          fontSize: 12,
                          color: Colors.amber[900],
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
        Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: Colors.blue[50],
            borderRadius: BorderRadius.circular(8),
          ),
          child: Icon(icon, color: Colors.blue[700], size: 20),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: const TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                description,
                style: TextStyle(
                  fontSize: 13,
                  color: Colors.grey[700],
                  height: 1.4,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  void _showAddContactDialog() {
    _nameController.clear();
    _phoneController.clear();
    _customRelationController.clear();
    _selectedRelation = null;
    _phoneError = '';

    showDialog(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) {
          return AlertDialog(
            title: const Text('Add Emergency Contact'),
            content: Form(
              key: _formKey,
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    TextFormField(
                      controller: _nameController,
                      decoration: const InputDecoration(
                        labelText: 'Name',
                        prefixIcon: Icon(Icons.person_outline),
                      ),
                      validator: (v) => v == null || v.trim().isEmpty ? 'Enter name' : null,
                    ),
                    const SizedBox(height: 12),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        TextFormField(
                          controller: _phoneController,
                          keyboardType: TextInputType.number,
                          inputFormatters: [
                            FilteringTextInputFormatter.digitsOnly,
                          ],
                          decoration: const InputDecoration(
                            labelText: 'Phone Number',
                            prefixIcon: Icon(Icons.phone_outlined),
                            prefixText: '+27 ',
                            hintText: '838555008',
                          ),
                          onChanged: (value) {
                            setDialogState(() {
                              if (value.isEmpty) {
                                _phoneError = '';
                              } else if (value.length < 9) {
                                _phoneError = 'Phone number requires exactly 9 digits';
                              } else if (value.length > 9) {
                                _phoneError = 'Phone number cannot exceed 9 digits';
                              } else {
                                _phoneError = '';
                              }
                            });
                          },
                          validator: (v) {
                            if (v == null || v.trim().isEmpty) {
                              return 'Enter phone number';
                            }
                            if (v.trim().length != 9) {
                              return null; // Don't show duplicate error
                            }
                            return null;
                          },
                        ),
                        if (_phoneError.isNotEmpty) ...[
                          const SizedBox(height: 4),
                          Padding(
                            padding: const EdgeInsets.only(left: 12),
                            child: Text(
                              _phoneError,
                              style: const TextStyle(
                                color: Colors.red,
                                fontSize: 12,
                              ),
                            ),
                          ),
                        ],
                      ],
                    ),
                    const SizedBox(height: 12),
                    DropdownButtonFormField<String>(
                      value: _selectedRelation,
                      decoration: const InputDecoration(
                        labelText: 'Relation',
                        prefixIcon: Icon(Icons.people_outline),
                      ),
                      hint: const Text('Select relation'),
                      items: _relationOptions.map((relation) {
                        return DropdownMenuItem(
                          value: relation,
                          child: Text(relation),
                        );
                      }).toList(),
                      onChanged: (value) {
                        setDialogState(() {
                          _selectedRelation = value;
                          if (value != 'Custom') {
                            _customRelationController.clear();
                          }
                        });
                      },
                      validator: (v) => v == null ? 'Select a relation' : null,
                    ),
                    if (_selectedRelation == 'Custom') ...[
                      const SizedBox(height: 12),
                      TextFormField(
                        controller: _customRelationController,
                        decoration: const InputDecoration(
                          labelText: 'Custom Relation',
                          prefixIcon: Icon(Icons.edit_outlined),
                          hintText: 'e.g., Cousin, Neighbor',
                        ),
                        validator: (v) =>
                            v == null || v.trim().isEmpty ? 'Enter custom relation' : null,
                      ),
                    ],
                  ],
                ),
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(context).pop(),
                child: const Text('Cancel'),
              ),
              ElevatedButton(
                onPressed: _phoneError.isEmpty ? _addContact : null,
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color.fromARGB(255, 143, 169, 255),
                  disabledBackgroundColor: Colors.grey[300],
                ),
                child: const Text('Add'),
              ),
            ],
          );
        },
      ),
    );
  }

  void _showEditContactDialog(EmergencyContact contact) {
    _nameController.text = contact.name;
    
    // Extract phone number without +27 prefix
    String phoneWithoutPrefix = contact.phone;
    if (phoneWithoutPrefix.startsWith('+27')) {
      phoneWithoutPrefix = phoneWithoutPrefix.substring(3);
    }
    _phoneController.text = phoneWithoutPrefix;
    _phoneError = '';
    
    // Set relation
    final relation = contact.relationType ?? '';
    if (_relationOptions.contains(relation)) {
      _selectedRelation = relation;
      _customRelationController.clear();
    } else if (relation.isNotEmpty) {
      _selectedRelation = 'Custom';
      _customRelationController.text = relation;
    } else {
      _selectedRelation = null;
      _customRelationController.clear();
    }

    showDialog(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) {
          return AlertDialog(
            title: const Text('Edit Emergency Contact'),
            content: Form(
              key: _formKey,
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    TextFormField(
                      controller: _nameController,
                      decoration: const InputDecoration(
                        labelText: 'Name',
                        prefixIcon: Icon(Icons.person_outline),
                      ),
                      validator: (v) => v == null || v.trim().isEmpty ? 'Enter name' : null,
                    ),
                    const SizedBox(height: 12),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        TextFormField(
                          controller: _phoneController,
                          keyboardType: TextInputType.number,
                          inputFormatters: [
                            FilteringTextInputFormatter.digitsOnly,
                          ],
                          decoration: const InputDecoration(
                            labelText: 'Phone Number',
                            prefixIcon: Icon(Icons.phone_outlined),
                            prefixText: '+27 ',
                            hintText: '838555008',
                          ),
                          onChanged: (value) {
                            setDialogState(() {
                              if (value.isEmpty) {
                                _phoneError = '';
                              } else if (value.length < 9) {
                                _phoneError = 'Phone number requires exactly 9 digits';
                              } else if (value.length > 9) {
                                _phoneError = 'Phone number cannot exceed 9 digits';
                              } else {
                                _phoneError = '';
                              }
                            });
                          },
                          validator: (v) {
                            if (v == null || v.trim().isEmpty) {
                              return 'Enter phone number';
                            }
                            if (v.trim().length != 9) {
                              return null; // Don't show duplicate error
                            }
                            return null;
                          },
                        ),
                        if (_phoneError.isNotEmpty) ...[
                          const SizedBox(height: 4),
                          Padding(
                            padding: const EdgeInsets.only(left: 12),
                            child: Text(
                              _phoneError,
                              style: const TextStyle(
                                color: Colors.red,
                                fontSize: 12,
                              ),
                            ),
                          ),
                        ],
                      ],
                    ),
                    const SizedBox(height: 12),
                    DropdownButtonFormField<String>(
                      value: _selectedRelation,
                      decoration: const InputDecoration(
                        labelText: 'Relation',
                        prefixIcon: Icon(Icons.people_outline),
                      ),
                      hint: const Text('Select relation'),
                      items: _relationOptions.map((relation) {
                        return DropdownMenuItem(
                          value: relation,
                          child: Text(relation),
                        );
                      }).toList(),
                      onChanged: (value) {
                        setDialogState(() {
                          _selectedRelation = value;
                          if (value != 'Custom') {
                            _customRelationController.clear();
                          }
                        });
                      },
                      validator: (v) => v == null ? 'Select a relation' : null,
                    ),
                    if (_selectedRelation == 'Custom') ...[
                      const SizedBox(height: 12),
                      TextFormField(
                        controller: _customRelationController,
                        decoration: const InputDecoration(
                          labelText: 'Custom Relation',
                          prefixIcon: Icon(Icons.edit_outlined),
                          hintText: 'e.g., Cousin, Neighbor',
                        ),
                        validator: (v) =>
                            v == null || v.trim().isEmpty ? 'Enter custom relation' : null,
                      ),
                    ],
                  ],
                ),
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(context).pop(),
                child: const Text('Cancel'),
              ),
              ElevatedButton(
                onPressed: _phoneError.isEmpty ? () => _updateContact(contact) : null,
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color.fromARGB(255, 123, 182, 255),
                  disabledBackgroundColor: Colors.grey[300],
                ),
                child: const Text('Update'),
              ),
            ],
          );
        },
      ),
    );
  }

  void _showDeleteConfirmation(EmergencyContact contact) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Contact'),
        content: Text('Are you sure you want to delete ${contact.name}?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.of(context).pop();
              _deleteContact(contact.id);
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color.fromARGB(255, 239, 116, 107),
            ),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.grey[50],
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: Colors.black),
          onPressed: () => Navigator.of(context).pop(),
        ),
        title: const Text(
          'Emergency Contacts',
          style: TextStyle(color: Colors.black, fontWeight: FontWeight.w600),
        ),
        centerTitle: true,
        actions: [
          IconButton(
            icon: const Icon(Icons.add, color: Color.fromARGB(255, 65, 144, 255)),
            onPressed: _showAddContactDialog,
            tooltip: 'Add Contact',
          ),
          IconButton(
            onPressed: _showHelpDialog,
            icon: Container(
              width: 32,
              height: 32,
              decoration: BoxDecoration(
                color: Colors.grey[300],
                shape: BoxShape.circle,
              ),
              child: Icon(
                Icons.help_outline,
                color: Colors.grey[700],
                size: 18,
              ),
            ),
            tooltip: 'Help & Support',
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _contacts.isEmpty
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(
                        Icons.contacts_outlined,
                        size: 64,
                        color: Colors.grey[400],
                      ),
                      const SizedBox(height: 16),
                      Text(
                        'No contacts yet',
                        style: TextStyle(
                          color: Colors.grey[600],
                          fontSize: 18,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Tap + to add your first emergency contact',
                        style: TextStyle(
                          color: Colors.grey[500],
                          fontSize: 14,
                        ),
                        textAlign: TextAlign.center,
                      ),
                    ],
                  ),
                )
              : ListView.separated(
                  padding: const EdgeInsets.all(16),
                  itemCount: _contacts.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 12),
                  itemBuilder: (context, index) {
                    final c = _contacts[index];
                    return Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(12),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withOpacity(0.05),
                            blurRadius: 10,
                            offset: const Offset(0, 2),
                          )
                        ],
                      ),
                      child: Row(
                        children: [
                          CircleAvatar(
                            radius: 24,
                            backgroundColor: const Color(0xFFE8D5FF),
                            child: Text(
                              c.name.isNotEmpty ? c.name[0].toUpperCase() : '?',
                              style: const TextStyle(
                                color: Color.fromARGB(255, 88, 143, 239),
                                fontWeight: FontWeight.w600,
                                fontSize: 18,
                              ),
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  c.name,
                                  style: const TextStyle(
                                    fontSize: 16,
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  c.phone,
                                  style: TextStyle(
                                    fontSize: 14,
                                    color: Colors.grey[700],
                                  ),
                                ),
                                if (c.relationType != null && c.relationType!.isNotEmpty)
                                  Padding(
                                    padding: const EdgeInsets.only(top: 4),
                                    child: Container(
                                      padding: const EdgeInsets.symmetric(
                                        horizontal: 8,
                                        vertical: 2,
                                      ),
                                      decoration: BoxDecoration(
                                        color: const Color.fromARGB(255, 222, 243, 255),
                                        borderRadius: BorderRadius.circular(4),
                                      ),
                                      child: Text(
                                        c.relationType!,
                                        style: const TextStyle(
                                          fontSize: 12,
                                          color: Color.fromARGB(116, 0, 0, 0),
                                          fontWeight: FontWeight.w500,
                                        ),
                                      ),
                                    ),
                                  ),
                              ],
                            ),
                          ),
                          IconButton(
                            icon: const Icon(Icons.edit_outlined, color: Color.fromARGB(255, 68, 154, 252)),
                            onPressed: () => _showEditContactDialog(c),
                          ),
                          IconButton(
                            icon: const Icon(Icons.delete_outline, color: Colors.red),
                            onPressed: () => _showDeleteConfirmation(c),
                          ),
                        ],
                      ),
                    );
                  },
                ),
    );
  }
}