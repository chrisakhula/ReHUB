import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../api/client";
import {
  Empty,
  ErrorNotice,
  Loading,
  Pagination,
} from "../../components/Common";
import { RecordDetails } from "./ResourcePanel";
import type { Entity } from "./types";

export function HistoryPanel({ path }: { path: string }) {
  const [page, setPage] = useState(1);
  const query = useQuery({
    queryKey: ["record-history", path, page],
    queryFn: () =>
      api<{ items: Entity[]; meta?: { total: number } }>(
        `${path}${path.includes("?") ? "&" : "?"}page=${page}`,
      ),
  });
  return (
    <details className="mt-4">
      <summary>Revision / correction history</summary>
      <ErrorNotice error={query.error} />
      {query.isPending ? (
        <Loading />
      ) : query.data?.items.length ? (
        query.data.items.map((row, i) => (
          <details key={row.id} className="history-entry">
            <summary>
              Record {i + 1}
              {row.version ? ` · Version ${row.version}` : ""} ·{" "}
              {String(row.created_at).slice(0, 10)}
            </summary>
            <RecordDetails record={row} />
            {query.data?.meta && (
              <Pagination
                page={page}
                total={query.data.meta.total}
                onChange={setPage}
              />
            )}
          </details>
        ))
      ) : (
        <Empty>No corrections recorded.</Empty>
      )}
    </details>
  );
}
