from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
import pandas as pd, numpy as np, io, datetime
from faker import Faker

fake = Faker("fr_FR")

def dashboard(request): 
    return render(request, "bluerose/dashboard.html")

def generer_page(request): 
    return render(request, "bluerose/generer.html")

def importer_page(request): 
    return render(request, "bluerose/importer.html")



@csrf_exempt
def upload_csv(request):
    if request.method in ["POST", "GET"]:
        n = int(request.POST.get("n_etudiants") or request.GET.get("n_etudiants", 0))
        if n <= 0:
            return JsonResponse({"error": "Nombre d'étudiants invalide"}, status=400)

        catalogue = pd.read_csv("UEEPL_ROSE.csv", sep=";", encoding="utf-8")
        df = generer_donnees(catalogue, n)
        request.session["enriched_csv"] = df.to_csv(sep=";", index=False)

        # renvoyer aussi un aperçu des données
        preview = df.head(20).to_dict(orient="records")
        return JsonResponse({"message": f"{n} étudiants générés", "preview": preview})
    return JsonResponse({"error": "Méthode non autorisée"}, status=405)





def generer_donnees(catalogue_df, n):
    enseignants_map, lignes = {}, []
    for i in range(n):
        parcours = np.random.choice(catalogue_df["license"].dropna().unique())
        semestre = np.random.choice(catalogue_df["semestre"].dropna().unique())
        ue_df = catalogue_df[(catalogue_df["license"] == parcours) & (catalogue_df["semestre"] == semestre)]

        etudiant = fake.name()
        genre = np.random.choice(["Homme", "Femme"])
        age = np.random.randint(18, 26)

        for _, row in ue_df.iterrows():
            code = row["code"]
            if code not in enseignants_map:
                enseignants_map[code] = fake.name()

            note = np.clip(np.random.normal(12, 3), 0, 20)
            lignes.append({
                "Etudiant": etudiant,
                "Genre": genre,
                "Age": age,
                "Parcours": parcours,
                "semestre": semestre,
                "UE-Code": code,
                "UE-intituler": row["intituler"],
                "Professeur": enseignants_map[code],
                "Credit": row["credit"],
                "Note": round(note, 2)
            })
    return pd.DataFrame(lignes)


def _apply_filters(df, params):
    if params is None:
        return df
    prof = params.get('professeur')
    parcours = params.get('parcours')
    semestre = params.get('semestre')
    matiere = params.get('matiere')
    if prof:
        df = df[df['Professeur'] == prof]
    if parcours:
        df = df[df['Parcours'] == parcours]
    if semestre:
        df = df[df['semestre'] == semestre]
    if matiere:
        df = df[df['UE-Code'] == matiere]
    return df



@csrf_exempt
def upload_user_csv(request):
    """Charge directement un CSV fourni par l'utilisateur"""
    if request.method == "POST" and request.FILES.get("csv_file"):
        df = pd.read_csv(request.FILES["csv_file"], sep=";", encoding="utf-8")
        request.session["enriched_csv"] = df.to_csv(sep=";", index=False)
        return JsonResponse({"message": "CSV utilisateur chargé"})
    return JsonResponse({"error": "Fichier manquant"}, status=400)



def stats(request):
    enriched_csv = request.session.get("enriched_csv")
    if not enriched_csv:
        return JsonResponse({"error": "Aucune donnée"}, status=400)

    df = pd.read_csv(io.StringIO(enriched_csv), sep=";")

    df = _apply_filters(df, request.GET)

    stats_globales = {
        "nb_etudiants": df["Etudiant"].nunique(),
        "nb_ue": df["UE-Code"].nunique() if "UE-Code" in df else None,
        "moyenne": round(df["Note"].mean(), 2) if not df.empty else None,
        "mediane": round(df["Note"].median(), 2) if not df.empty else None,
        "ecart_type": round(df["Note"].std(), 2) if not df.empty else None,
        "taux_reussite": round((df["Note"] >= 10).mean() * 100, 2) if not df.empty else None,
    }

    stats_par_matiere, stats_par_parcours, stats_par_genre, stats_par_age = [], [], [], []

    if not df.empty:
        for ue, group in df.groupby("UE-Code"):
            notes = group["Note"]
            stats_par_matiere.append({
                "UE": ue,
                "moyenne": round(notes.mean(), 2),
                "mediane": round(notes.median(), 2),
                "ecart_type": round(notes.std(), 2),
                "taux_reussite": round((notes >= 10).mean() * 100, 2),
                "distribution": notes.tolist(),
                "Professeur": group["Professeur"].iloc[0],
                "semestre": group["semestre"].iloc[0]
            })
        for parcours, notes in df.groupby("Parcours")["Note"]:
            stats_par_parcours.append({
                "Parcours": parcours,
                "moyenne": round(notes.mean(), 2),
                "mediane": round(notes.median(), 2),
                "ecart_type": round(notes.std(), 2),
                "taux_reussite": round((notes >= 10).mean() * 100, 2),
                "nb_etudiants": int((df[df["Parcours"] == parcours]["Etudiant"].nunique()))
            })
        for genre, notes in df.groupby("Genre")["Note"]:
            stats_par_genre.append({
                "Genre": genre,
                "moyenne": round(notes.mean(), 2),
                "mediane": round(notes.median(), 2),
                "ecart_type": round(notes.std(), 2),
                "taux_reussite": round((notes >= 10).mean() * 100, 2),
                "nb_etudiants": int(df[df["Genre"] == genre]["Etudiant"].nunique())
            })
        for age, notes in df.groupby("Age")["Note"]:
            stats_par_age.append({
                "Age": age,
                "moyenne": round(notes.mean(), 2),
                "mediane": round(notes.median(), 2),
                "ecart_type": round(notes.std(), 2),
                "taux_reussite": round((notes >= 10).mean() * 100, 2),
                "nb_etudiants": int(df[df["Age"] == age]["Etudiant"].nunique())
            })

    return JsonResponse({
        "global": stats_globales,
        "par_matiere": stats_par_matiere,
        "par_parcours": stats_par_parcours,
        "par_genre": stats_par_genre,
        "par_age": stats_par_age
    })




def exporter_donnee(request):
    enriched_csv = request.session.get("enriched_csv")
    if not enriched_csv:
        return JsonResponse({"error": "Aucun fichier"}, status=400)

    filename = f"donnees_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    response = HttpResponse(enriched_csv, content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename={filename}'
    return response


def _build_chart_payload(df):
    df = df.copy()
    # ensure numeric notes
    if "Note" in df:
        df["Note"] = pd.to_numeric(df["Note"], errors="coerce").fillna(0)

    charts = {}

    # Histogram of notes
    if "Note" in df and not df["Note"].empty:
        counts, bins = np.histogram(df["Note"], bins=10)
        charts["histogram"] = {"bins": bins.tolist(), "counts": counts.tolist()}

    # Average per UE
    if "UE-Code" in df:
        ue_avg = df.groupby("UE-Code")["Note"].mean().round(2)
        charts["avg_per_ue"] = {"labels": ue_avg.index.tolist(), "values": ue_avg.tolist()}

    # Average per parcours
    if "Parcours" in df:
        parcours_avg = df.groupby("Parcours")["Note"].mean().round(2)
        charts["avg_per_parcours"] = {"labels": parcours_avg.index.tolist(), "values": parcours_avg.tolist()}

    # Gender distribution
    if "Genre" in df:
        gender_counts = df["Genre"].value_counts()
        charts["gender"] = {"labels": gender_counts.index.tolist(), "values": gender_counts.tolist()}

    # Age distribution
    if "Age" in df:
        age_counts = df["Age"].value_counts().sort_index()
        charts["age"] = {"labels": age_counts.index.astype(str).tolist(), "values": age_counts.tolist()}

    # Scatter: Credit vs Note
    if "Credit" in df and "Note" in df:
        scatter = df[["Credit", "Note"]].dropna().to_dict(orient="records")
        charts["scatter_credit_note"] = scatter

    # Average per semestre
    if "semestre" in df:
        sem_avg = df.groupby("semestre")["Note"].mean().round(2)
        charts["avg_per_semestre"] = {"labels": sem_avg.index.tolist(), "values": sem_avg.tolist()}

    # Provide raw per-UE distributions (useful for boxplots on client side/plugins)
    if "UE-Code" in df:
        per_ue = {ue: group["Note"].tolist() for ue, group in df.groupby("UE-Code")}
        charts["per_ue_distribution"] = per_ue

    return charts


def charts_data(request):
    enriched_csv = request.session.get("enriched_csv")
    if not enriched_csv:
        return JsonResponse({"error": "Aucune donnée"}, status=400)

    df_full = pd.read_csv(io.StringIO(enriched_csv), sep=";")
    available_filters = {
        "professeur": sorted(df_full["Professeur"].dropna().unique().tolist()) if "Professeur" in df_full else [],
        "parcours": sorted(df_full["Parcours"].dropna().unique().tolist()) if "Parcours" in df_full else [],
        "semestre": sorted(df_full["semestre"].dropna().unique().tolist()) if "semestre" in df_full else [],
        "matiere": sorted(df_full["UE-Code"].dropna().unique().tolist()) if "UE-Code" in df_full else [],
        "age": sorted(map(int, df_full["Age"].dropna().unique().tolist())) if "Age" in df_full else [],
        "credit": sorted(df_full["Credit"].dropna().unique().tolist()) if "Credit" in df_full else [],
    }

    df = _apply_filters(df_full, request.GET)
    payload = _build_chart_payload(df)
    return JsonResponse({"charts": payload, "available_filters": available_filters, "applied_filters": dict(request.GET)})
