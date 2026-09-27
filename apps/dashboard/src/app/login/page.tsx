type LoginPageProps = {
  searchParams: Promise<{ error?: string }>;
};

const messages: Record<string, string> = {
  missing: "Email and password are required.",
  invalid: "Invalid credentials.",
  unavailable: "The API is currently unavailable.",
};

export default async function LoginPage({ searchParams }: LoginPageProps) {
  const params = await searchParams;
  const error = params.error ? messages[params.error] : undefined;

  return (
    <main className="authPage">
      <section className="card authCard">
        <div className="eyebrow">AI Web Agency</div>
        <h1>Sign in</h1>
        <p className="muted">Access your agency operations dashboard.</p>
        {error ? <p className="error">{error}</p> : null}
        <form action="/api/auth/login" method="post" className="authForm">
          <label>
            Email
            <input name="email" type="email" autoComplete="email" required />
          </label>
          <label>
            Password
            <input name="password" type="password" autoComplete="current-password" required />
          </label>
          <button className="button" type="submit">Sign in</button>
        </form>
      </section>
    </main>
  );
}
