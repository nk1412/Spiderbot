// ignore_for_file: use_build_context_synchronously, avoid_print

import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:cloud_firestore/cloud_firestore.dart'; // Import Cloud Firestore package
import 'firebase_options.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp(
    options: DefaultFirebaseOptions.currentPlatform,
  );
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Firebase Authentication Demo',
      theme: ThemeData(
        primarySwatch: Colors.blue,
      ),
      home: const LoginPage(),
    );
  }
}

class LoginPage extends StatefulWidget {
  const LoginPage({super.key});

  @override
  // ignore: library_private_types_in_public_api
  _LoginPageState createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final TextEditingController _emailController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();

  Future<void> _signInWithEmailAndPassword() async {
    try {
      UserCredential userCredential = await FirebaseAuth.instance.signInWithEmailAndPassword(
        email: _emailController.text,
        password: _passwordController.text,
      );
      print('User signed in: ${userCredential.user!.uid}');
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (context) => HomePage(userCredential.user!.uid)), // Pass user UID to HomePage
      );
    } catch (e) {
      print('Failed to sign in: $e');
    }
  }

  Future<void> _signUpWithEmailAndPassword() async {
    try {
      UserCredential userCredential = await FirebaseAuth.instance.createUserWithEmailAndPassword(
        email: _emailController.text,
        password: _passwordController.text,
      );
      print('User signed up: ${userCredential.user!.uid}');
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (context) => HomePage(userCredential.user!.uid)), // Pass user UID to HomePage
      );
    } catch (e) {
      print('Failed to sign up: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Login'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            TextField(
              controller: _emailController,
              decoration: const InputDecoration(labelText: 'Email'),
            ),
            const SizedBox(height: 8.0),
            TextField(
              controller: _passwordController,
              decoration: const InputDecoration(labelText: 'Password'),
              obscureText: true,
            ),
            const SizedBox(height: 16.0),
            ElevatedButton(
              onPressed: _signInWithEmailAndPassword,
              child: const Text('Sign In'),
            ),
            const SizedBox(height: 8.0),
            ElevatedButton(
              onPressed: _signUpWithEmailAndPassword,
              child: const Text('Sign Up'),
            ),
          ],
        ),
      ),
    );
  }
}

class HomePage extends StatelessWidget {
  final String userId;
  final TextEditingController _textController = TextEditingController();
  HomePage(this.userId, {super.key}); // Constructor to receive user UID

  final FirebaseFirestore _firestore = FirebaseFirestore.instance; // Reference to Firestore
  void updateTextInFirestore() {

  // _firestore.collection('users').doc('user2').set({'name': 'John', 'age': 30})
  _firestore.collection(userId).doc('my_document').set({'text': _textController.text})
    .then((_) {
      print('Document successfully updated!');
    })
    .catchError((error) {
      print('Failed to update document: $error');
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Home Page'),
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text(
              'Welcome to the Home Page!',
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 20),
            TextField(
              controller: _textController,
              decoration: const InputDecoration(labelText: 'input to update'),
            ),
            const SizedBox(height: 8.0),
            ElevatedButton(
              onPressed: () {
                updateTextInFirestore(); // Call the function to update text in Firestore
              },
              child: const Text('Update Text in Firestore'),
            ),
          ],
        ),
      ),
    );
  }
}
