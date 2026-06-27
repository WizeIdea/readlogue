import { signOut } from "@/app/actions";
import { Button } from "@/components/ui/button";

export function Header() {
  return (
    <header className="app-header">
      <div className="app-header-inner">
        <div>
          <h1 className="app-title">ReadLogue</h1>
          <p className="app-tagline">Research corpus curation</p>
        </div>
        <form action={signOut}>
          <Button type="submit" variant="outline" size="sm">
            Sign out
          </Button>
        </form>
      </div>
    </header>
  );
}
