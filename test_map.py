import plotly.graph_objects as go
import numpy as np

def create_raxxla_hunt_map():
    # --- 1. COORDINATE DATABASE (Approximate Game Coords) ---
    # Format: [X, Y, Z]
    # Sol is (0,0,0).
    # X: Left/Right, Y: Up/Down, Z: Front/Back (Galactic Plane)
    
    locations = {
        "Sol": np.array([0, 0, 0]),
        "Heart Nebula": np.array([-7200, -400, -2800]),
        "Soul Nebula": np.array([-7200, -400, -3200]),
        "Zurara (Syreadiae JX-F c0)": np.array([-11500, -150, -2500]),
        "Colonia": np.array([-9530, -910, 19800]), # Reference point
    }

    fig = go.Figure()

    # --- 2. PLOT KEY LANDMARKS ---
    # Plot Sol (Home)
    fig.add_trace(go.Scatter3d(
        x=[locations["Sol"][0]], y=[locations["Sol"][1]], z=[locations["Sol"][2]],
        mode='markers', marker=dict(size=8, color='yellow'),
        name='Sol (Bubble Center)'
    ))

    # Plot The Nebulae & Zurara
    for name, coords in locations.items():
        if name != "Sol":
            fig.add_trace(go.Scatter3d(
                x=[coords[0]], y=[coords[1]], z=[coords[2]],
                mode='markers', marker=dict(size=10, color='cyan', opacity=0.8),
                name=name
            ))

    # --- 3. CALCULATE SEARCH ZONES (THEORY IMPLEMENTATION) ---

    # ZONE A: "Brow of the Mother" (Cassiopeia Vector)
    # Vector from Sol towards the midpoint of Heart/Soul (General Cassiopeia direction)
    hs_midpoint = (locations["Heart Nebula"] + locations["Soul Nebula"]) / 2
    # Create a line trace
    fig.add_trace(go.Scatter3d(
        x=[0, hs_midpoint[0]], y=[0, hs_midpoint[1]], z=[0, hs_midpoint[2]],
        mode='lines', line=dict(color='white', width=2, dash='dash'),
        name='Cassiopeia Line-of-Sight'
    ))
    # Target Highlight: 1/3rd of the way out
    zone_a = hs_midpoint * 0.33
    fig.add_trace(go.Scatter3d(
        x=[zone_a[0]], y=[zone_a[1]], z=[zone_a[2]],
        mode='markers', marker=dict(size=15, color='red', opacity=0.5, symbol='diamond'),
        name='ZONE A: The Brow (Anchor System?)'
    ))

    # ZONE B: "Vagabond Crossroads" (Triangle Center)
    # Centroid of Triangle: Sol, Heart Nebula, Zurara
    centroid = (locations["Sol"] + locations["Heart Nebula"] + locations["Zurara (Syreadiae JX-F c0)"]) / 3
    fig.add_trace(go.Scatter3d(
        x=[centroid[0]], y=[centroid[1]], z=[centroid[2]],
        mode='markers', marker=dict(size=20, color='orange', opacity=0.4),
        name='ZONE B: Vagabond Crossroads'
    ))

    # ZONE C: "The Dark Heart" (Void between Heart & Soul)
    # Exact midpoint between Heart and Soul
    void_target = (locations["Heart Nebula"] + locations["Soul Nebula"]) / 2
    fig.add_trace(go.Scatter3d(
        x=[void_target[0]], y=[void_target[1]], z=[void_target[2]],
        mode='markers', marker=dict(size=12, color='purple', symbol='circle-open'),
        name='ZONE C: The Void Between'
    ))

    # --- 4. VISUAL STYLING (The "Conspiracy Board" Look) ---
    fig.update_layout(
        title="Op Omphalos Gate: Raxxla Search Potential Map",
        scene=dict(
            xaxis=dict(backgroundcolor="black", gridcolor="gray", showbackground=True, zerolinecolor="white"),
            yaxis=dict(backgroundcolor="black", gridcolor="gray", showbackground=True, zerolinecolor="white"),
            zaxis=dict(backgroundcolor="black", gridcolor="gray", showbackground=True, zerolinecolor="white"),
            aspectmode='data' # Keeps the scale realistic
        ),
        paper_bgcolor="black",
        font=dict(color="white"),
        margin=dict(r=0, l=0, b=0, t=50),
        legend=dict(yanchor="top", y=0.9, xanchor="left", x=0.1)
    )

    fig.show()

if __name__ == "__main__":
    create_raxxla_hunt_map()