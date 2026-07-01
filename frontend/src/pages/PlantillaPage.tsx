import { useEffect, useRef, useState } from "react";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Textarea } from "../components/ui/textarea";
import { getPlantilla, updatePlantilla } from "../services/plantilla";
import type { Plantilla } from "../types/domain";

const VARIABLES = [
  "{{nombre}}",
  "{{monto}}",
  "{{localidad}}",
  "{{clave_union}}",
  "{{fecha_envio}}",
];

const DEFAULTS: Plantilla = {
  asunto: "Recordatorio de deuda",
  cuerpo_html:
    "<p>Estimado <strong>{{nombre}}</strong>,</p><p>Le informamos que registra una deuda con nuestra empresa. Quedo a disposición ante cualquier consulta.</p>",
  nombre_empresa: "",
  logo_url: null,
  color_primario: "#1a56db",
  monto_minimo: 0,
};

export default function PlantillaPage() {
  const [form, setForm] = useState<Plantilla>(DEFAULTS);
  const [status, setStatus] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  function insertarVariable(variable: string) {
    const el = textareaRef.current;
    if (!el) return;
    const start = el.selectionStart ?? form.cuerpo_html.length;
    const end = el.selectionEnd ?? form.cuerpo_html.length;
    const next = form.cuerpo_html.slice(0, start) + variable + form.cuerpo_html.slice(end);
    set("cuerpo_html", next);
    requestAnimationFrame(() => {
      el.focus();
      const pos = start + variable.length;
      el.setSelectionRange(pos, pos);
    });
  }

  useEffect(() => {
    getPlantilla().then(setForm).catch(console.error);
  }, []);

  function set(field: keyof Plantilla, value: string | number | null) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSave() {
    setStatus("Guardando...");
    try {
      await updatePlantilla(form);
      setStatus("Guardado correctamente");
    } catch {
      setStatus("Error al guardar");
    }
  }

  return (
    <div className="p-6 max-w-2xl space-y-4">
      <h1 className="text-2xl font-bold">Plantilla de Mail</h1>
      <div className="space-y-3">
        <label className="block text-sm font-medium">Asunto</label>
        <Input value={form.asunto} onChange={(e) => set("asunto", e.target.value)} />

        <label className="block text-sm font-medium">Cuerpo HTML</label>
        <div className="flex flex-wrap gap-1.5">
          {VARIABLES.map((v) => (
            <button
              key={v}
              type="button"
              onClick={() => insertarVariable(v)}
              className="px-2 py-1 text-xs font-mono bg-slate-100 hover:bg-slate-200 text-slate-700 rounded border border-slate-200 transition-colors"
            >
              {v}
            </button>
          ))}
        </div>
        <Textarea
          ref={textareaRef}
          rows={8}
          value={form.cuerpo_html}
          onChange={(e) => set("cuerpo_html", e.target.value)}
          className="font-mono text-sm"
        />

        <label className="block text-sm font-medium">Nombre empresa</label>
        <Input
          value={form.nombre_empresa}
          onChange={(e) => set("nombre_empresa", e.target.value)}
        />

        <label className="block text-sm font-medium">Color primario (hex)</label>
        <div className="flex gap-2 items-center">
          <input
            type="color"
            value={form.color_primario}
            onChange={(e) => set("color_primario", e.target.value)}
          />
          <Input
            value={form.color_primario}
            onChange={(e) => set("color_primario", e.target.value)}
            className="w-32"
          />
        </div>

        <label className="block text-sm font-medium">Monto mínimo de envío ($)</label>
        <Input
          type="number"
          value={form.monto_minimo}
          onChange={(e) => set("monto_minimo", Number(e.target.value))}
        />
      </div>
      {status && <p className="text-sm text-gray-600">{status}</p>}
      <Button onClick={handleSave}>Guardar plantilla</Button>
    </div>
  );
}
