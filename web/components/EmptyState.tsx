import Link from "next/link";

export function EmptyState({ message }: { message?: string }) {
  return (
    <div className="card p-8 text-center">
      <p className="text-lg">No forecast yet</p>
      <p className="mt-2 text-sm text-mist">
        {message ||
          "Ingest a local repo to see a heuristic weather forecast from that repo's own history."}
      </p>
      <Link href="/ingest" className="mt-4 inline-block rounded-lg bg-sky-500/20 px-4 py-2 text-sky-100">
        Open ingest
      </Link>
    </div>
  );
}
