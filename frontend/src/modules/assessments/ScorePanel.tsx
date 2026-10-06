import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { Form } from "react-bootstrap";
import { api, save } from "../../api/client";
import { useAuth } from "../../auth/AuthProvider";
import { ErrorNotice } from "../../components/Common";
import { RecordForm } from "../care/RecordForm";
import { ResourcePanel } from "../care/ResourcePanel";
import { stamp, note } from "../care/fields";
import type { Field, Entity, Values } from "../care/types";
import type { Page } from "../../types/identity";

interface Tool extends Entity {
  code: string;
  name: string;
  version: number;
  instructions: string;
  questions: {
    key: string;
    text: string;
    options: { value: string; label: string }[];
  }[];
}
export function ScorePanel() {
  const auth = useAuth();
  const [params] = useSearchParams();
  const [selected, setSelected] = useState("");
  const [page, setPage] = useState(1);
  const cache = useQueryClient();
  const tools = useQuery({
    queryKey: ["scoring-instruments", page],
    queryFn: () => api<Page<Tool>>(`/rehabilitation/instruments?page=${page}`),
  });
  const tool = tools.data?.items.find((t) => t.id === selected);
  const admissionId = params.get("admission_id") ?? "";
  const trends = useQuery({
    queryKey: ["score-trend", admissionId, tool?.id],
    queryFn: () =>
      api<Page<Entity>>(
        `/rehabilitation/score-trends?admission_id=${admissionId}&instrument_id=${tool?.id ?? ""}&page_size=100&sort=completed_at&direction=asc`,
      ),
    enabled: !!admissionId && !!tool,
  });
  const scores = trends.data?.items ?? [];
  const max = Math.max(1, ...scores.map((s) => Number(s.score)));
  const fields: Field[] = tool
    ? [
        stamp("completed_at", "Completion time", true),
        {
          name: "responses",
          label: "Assessment responses",
          type: "object",
          required: true,
          fields: tool.questions.map((q) => ({
            name: q.key,
            label: q.text,
            type: "select",
            required: true,
            options: q.options.map((o) => ({ value: o.value, label: o.label })),
          })),
        },
        note("notes", "Assessment notes"),
      ]
    : [];
  return (
    <section className="card card-body mb-4">
      <h2 className="mb-3">Structured assessment & score trends</h2>
      <Form.Group controlId="score-tool">
        <Form.Label>Assessment instrument</Form.Label>
        <Form.Select
          value={selected}
          onChange={(e) => setSelected(e.target.value)}
        >
          <option value="">Choose a configured instrument</option>
          {tools.data?.items.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name} · Version {t.version}
            </option>
          ))}
        </Form.Select>
      </Form.Group>
      <div className="d-flex gap-2 mt-2">
        <button
          className="btn btn-sm btn-outline-secondary"
          disabled={page === 1}
          onClick={() => setPage(page - 1)}
        >
          Previous instruments
        </button>
        <button
          className="btn btn-sm btn-outline-secondary"
          disabled={page * 20 >= (tools.data?.meta.total ?? 0)}
          onClick={() => setPage(page + 1)}
        >
          Next instruments
        </button>
      </div>
      <ErrorNotice error={tools.error || trends.error} />
      {tool && (
        <>
          <p className="mt-3">{tool.instructions}</p>
          {admissionId && auth.can("assessment.record") && (
            <RecordForm
              key={tool.id}
              fields={fields}
              onSubmit={async (data) => {
                await save("/rehabilitation/scores", {
                  ...data,
                  admission_id: admissionId,
                  instrument_id: tool.id,
                });
                await cache.invalidateQueries();
              }}
            />
          )}
          {scores.length > 0 && (
            <figure className="mt-4">
              <figcaption>
                Recorded scores for {tool.name} (version {tool.version})
              </figcaption>
              <svg
                viewBox="0 0 600 170"
                role="img"
                aria-label={`Historical assessment scores: ${scores.map((s) => s.score).join(", ")}`}
                className="score-chart"
              >
                <path d="M35 10 V140 H580" fill="none" stroke="#93a3b0" />
                <polyline
                  fill="none"
                  stroke="#24577b"
                  strokeWidth="2"
                  points={scores
                    .map(
                      (s, i) =>
                        `${35 + i * (540 / Math.max(1, scores.length - 1))},${135 - (Number(s.score) / max) * 115}`,
                    )
                    .join(" ")}
                />
                {scores.map((s, i) => (
                  <g key={s.id}>
                    <circle
                      cx={35 + i * (540 / Math.max(1, scores.length - 1))}
                      cy={135 - (Number(s.score) / max) * 115}
                      r="4"
                      fill="#24577b"
                    />
                    <text
                      x={35 + i * (540 / Math.max(1, scores.length - 1))}
                      y={125 - (Number(s.score) / max) * 115}
                      fontSize="11"
                      textAnchor="middle"
                    >
                      {String(s.score)}
                    </text>
                  </g>
                ))}
                <text x="35" y="162" fontSize="10">
                  Earlier
                </text>
                <text x="545" y="162" fontSize="10">
                  Latest
                </text>
              </svg>
            </figure>
          )}
        </>
      )}
      <div className="mt-4">
        <ResourcePanel
          resource={{
            title: "Assessment scores",
            path: "/rehabilitation/scores",
            permission: "assessment.view",
            admissionScoped: true,
            columns: [
              { key: "completed_at", label: "Completed" },
              { key: "score", label: "Score" },
              { key: "interpretation", label: "Interpretation" },
              { key: "risk_level", label: "Risk" },
            ],
          }}
          context={{ admission_id: admissionId } as Values}
        />
      </div>
    </section>
  );
}
