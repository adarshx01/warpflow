import React from 'react';
import { AuthLayout } from '../components/auth/AuthLayout';
import { SignupForm } from '../components/auth/SignupForm';

const Signup: React.FC = () => {
  return (
    <AuthLayout 
      title="Create Account" 
      subtitle="Start automating your workflows in minutes"
    >
      <SignupForm />
    </AuthLayout>
  );
};

export default Signup;