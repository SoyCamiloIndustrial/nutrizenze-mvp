# app/models/patient_store.py
"""Almacén de pacientes en memoria (MVP).

Carga datos sintéticos desde app/data/demo_patients.json. Los cambios
(recomendaciones nuevas o aprobadas) viven en memoria y se pierden al
reiniciar; la persistencia real queda para una base de datos.
"""
import copy
import json
import os
import uuid

DEMO_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "demo_patients.json")


class PatientStore:
    def __init__(self, path=DEMO_FILE):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        self._patients = {p["id"]: p for p in copy.deepcopy(data["patients"])}
        for p in self._patients.values():
            p["reports"].sort(key=lambda r: r["date"])

    def all(self):
        return list(self._patients.values())

    def get(self, patient_id):
        return self._patients.get(patient_id)

    def add_recommendation(self, patient_id, text, author):
        rec = {"id": uuid.uuid4().hex[:8], "text": text, "author": author, "status": "aprobada"}
        self._patients[patient_id]["recommendations"].append(rec)
        return rec

    def set_recommendation_status(self, patient_id, rec_id, status):
        for rec in self._patients[patient_id]["recommendations"]:
            if rec["id"] == rec_id:
                rec["status"] = status
                return rec
        return None
