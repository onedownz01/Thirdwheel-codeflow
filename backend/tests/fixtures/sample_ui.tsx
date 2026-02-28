import { useRouter } from 'next/navigation';

export default function Signup() {
  const router = useRouter();

  const handleSubmit = async () => {
    await fetch('/api/users', { method: 'POST' });
    router.push('/welcome');
  };

  return (
    <form action={handleSubmit}>
      <button onClick={handleSubmit}>Sign Up</button>
    </form>
  );
}
