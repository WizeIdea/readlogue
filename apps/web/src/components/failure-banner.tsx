import { FailureActions } from "@/components/failure-actions";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import type { IngestionFailure } from "@/lib/types";

type Props = {
  failures: IngestionFailure[];
};

export function FailureBanner({ failures }: Props) {
  if (failures.length === 0) {
    return null;
  }

  return (
    <Alert variant="destructive">
      <AlertTitle>Ingestion failures</AlertTitle>
      <AlertDescription>
        These URLs failed validation and were not saved to the index.
      </AlertDescription>
      <div>
        {failures.map((failure) => (
          <div key={failure.id} className="failure-item">
            <p>
              <strong>{failure.source_name}</strong>
              {" · "}
              <a href={failure.article_url} target="_blank" rel="noopener noreferrer">
                {failure.article_url}
              </a>
            </p>
            <p>
              {failure.failure_count}{" "}
              {failure.failure_count === 1 ? "attempt" : "attempts"} — {failure.message}
            </p>
            <FailureActions
              articleUrl={failure.article_url}
              fingerprint={failure.article_fingerprint}
            />
          </div>
        ))}
      </div>
    </Alert>
  );
}
