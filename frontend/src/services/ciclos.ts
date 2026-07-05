import { apiFetch } from "./api";
import type { Envio, PreviewCiclo } from "../types/domain";

export async function previewCiclo(file: File): Promise<PreviewCiclo> {
  const form = new FormData();
  form.append("file", file);
  const r = await apiFetch("/ciclos/preview", { method: "POST", body: form });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(err.detail ?? "Error al procesar el Excel");
  }
  return r.json();
}

export function confirmarCiclo(
  file: File,
  onProgress: (data: { enviado: number; total: number; id?: string; done?: boolean }) => void,
): () => void {
  const form = new FormData();
  form.append("file", file);
  const token = localStorage.getItem("access_token");
  const controller = new AbortController();

  fetch(`${import.meta.env.VITE_API_URL ?? "http://localhost:8000"}/ciclos/confirmar`, {
    method: "POST",
    body: form,
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    signal: controller.signal,
  }).then(async (r) => {
    if (!r.ok || !r.body) return;
    const reader = r.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";
      for (const line of lines) {
        if (line.startsWith("data: ")) {
          try {
            onProgress(JSON.parse(line.slice(6)));
          } catch {}
        }
      }
    }
  });

  return () => controller.abort();
}

export async function getEnviosActivo(): Promise<Envio[]> {
  const r = await apiFetch("/ciclos/activo/envios");
  if (!r.ok) throw new Error("Error cargando envíos");
  return r.json();
}

export async function reenviarEnvio(id: string): Promise<Envio> {
  const r = await apiFetch(`/envios/${id}/reenviar`, { method: "POST" });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(err.detail ?? "Error al reenviar el mail");
  }
  return r.json();
}

export function reenviarFallidos(
  onProgress: (data: {
    enviado: number;
    total: number;
    id?: string;
    done?: boolean;
    saltados?: { id: string; motivo: string }[];
    error?: string;
  }) => void,
): () => void {
  const token = localStorage.getItem("access_token");
  const controller = new AbortController();

  fetch(`${import.meta.env.VITE_API_URL ?? "http://localhost:8000"}/ciclos/activo/reenviar-fallidos`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    signal: controller.signal,
  })
    .then(async (r) => {
      if (!r.ok || !r.body) {
        onProgress({ enviado: 0, total: 0, done: true, error: "Error al reenviar los mails" });
        return;
      }
      const reader = r.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              onProgress(JSON.parse(line.slice(6)));
            } catch {}
          }
        }
      }
    })
    .catch(() => {
      onProgress({ enviado: 0, total: 0, done: true, error: "Error al reenviar los mails" });
    });

  return () => controller.abort();
}
