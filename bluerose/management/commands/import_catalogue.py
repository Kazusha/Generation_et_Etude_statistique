import pandas as pd
from django.core.management.base import BaseCommand
from bluerose.models import Parcours, UE

class Command(BaseCommand):
    help = "Importe le catalogue des UE"

    def add_arguments(self, parser):
        parser.add_argument("--path", required=True, help="Chemin du fichier")

    def handle(self, *args, **opts):
        path = opts["path"]
        df = pd.read_csv(path, sep=";", encoding="utf-8")
        df.columns = df.columns.str.strip().str.lower()

        # Harmoniser les colonnes avec ton modèle
        df = df.rename(columns={"intituler": "intitule"})

        created_p = 0
        created_ue = 0

        for _, row in df.iterrows():
            parcours, p_created = Parcours.objects.get_or_create(nom=str(row["license"]).strip())
            if p_created:
                created_p += 1

            ue, ue_created = UE.objects.get_or_create(
                code=str(row["code"]).strip(),
                parcours=parcours,
                semeste=int(row["semestre"]) if pd.notna(row["semestre"]) and str(row["semestre"]).strip() != "" else None,
                defaults={
                    "intitule": str(row["intitule"]).strip(),
                    "credit": int(row["credit"]) if pd.notna(row["credit"]) and str(row["credit"]).strip() != "" else None,
                }
            )

            if not ue_created:
                ue.intitule = str(row["intitule"]).strip()
                ue.credit = int(row["credit"]) if pd.notna(row["credit"]) and str(row["credit"]).strip() != "" else None
                ue.save()
            else:
                created_ue += 1  

        self.stdout.write(self.style.SUCCESS(f"Parcours créés : {created_p}, UE créées : {created_ue}"))
