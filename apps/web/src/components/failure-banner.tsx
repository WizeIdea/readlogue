import { FailureActions } from "@/components/failure-actions";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { sourceDisplayNameLoose } from "@/lib/sources";
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
      <div className="failure-grid">
        {failures.map((failure) => (
          <div key={failure.id} className="failure-card">
            <h3 className="failure-card-title">
              <a
                href={failure.article_url}
                target="_blank"
                rel="noopener noreferrer"
              >
                {sourceDisplayNameLoose(failure.source_name)}
              </a>
            </h3>
            <p className="failure-card-message">
              {failure.failure_count}{" "}
              {failure.failure_count === 1 ? "attempt" : "attempts"} —{" "}
              {failure.message}
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
