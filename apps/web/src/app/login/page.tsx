import { LoginForm } from "@/components/login-form";

export default function LoginPage() {
  return (
    <div className="login-page">
      <div className="login-card">
        <h1 className="app-title">ReadLogue</h1>
        <p className="app-tagline">
          Curate technical research — like, dislike, and label articles for ML training.
        </p>
        <LoginForm />
      </div>
    </div>
  );
}
