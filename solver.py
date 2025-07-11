import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def palet_factor(pal_type):
    if isinstance(pal_type, str):
        pal_type = pal_type.strip().lower()
        if pal_type == 'kısa hafif':
            return 0.5
        elif pal_type == 'kısa ağır':
            return 0.5
        elif pal_type == 'yüksek palet':
            return 1
    return 1

def calculate_effective_pallet(row):
    try:
        return row['CPallet'] * palet_factor(row['PALTypeChoice'])
    except Exception:
        return 9999

def solve_assignment(order_df):
    order_df = order_df.copy().reset_index(drop=True)
    order_df['PALTypeChoice'] = order_df['PALTypeChoice'].fillna('').str.lower().str.strip()
    order_df['EffectivePallet'] = order_df.apply(calculate_effective_pallet, axis=1)

    assignments = []
    truck_counter = 1
    grouped = order_df.groupby(['Shipping Point/Receiving Pt', 'Location of the ship-to party'])

    for (ship_point, ship_to), group in grouped:
        group = group.copy().reset_index(drop=True)
        used = [False] * len(group)

        while not all(used):
            truck_id = f"Truck-{truck_counter}"
            slots_bottom = [None] * 33  # alt kat slotları
            slots_top = [None] * 33     # üst kat slotları
            total_effective = 0.0
            assigned_ids = set()

            # 1. ALT kata yüksek palet + kısa ağırları yerleştir
            sorted_group = group[~pd.Series(used)].copy()
            sorted_group['SortOrder'] = sorted_group['PALTypeChoice'].map({
                'yüksek palet': 1,
                'kısa ağır': 2,
                'kısa hafif': 3
            }).fillna(4)
            sorted_group = sorted_group.sort_values(by='SortOrder')

            slot_i = 0
            for idx, row in sorted_group.iterrows():
                if used[idx]:
                    continue
                if row['PALTypeChoice'] not in ['yüksek palet', 'kısa ağır']:
                    continue
                needed_slots = int(np.ceil(row['CPallet']))  # gerçek palet sayısı ile hesapla
                if slot_i + needed_slots <= 33:
                    for s in range(needed_slots):
                        slots_bottom[slot_i] = idx
                        slot_i += 1
                    total_effective += row['EffectivePallet']
                    used[idx] = True
                    assigned_ids.add(idx)

            # 2. kısa hafif → önce kısa ağırların üstüne
            for idx, bottom_idx in enumerate(slots_bottom):
                if bottom_idx is None:
                    continue
                bottom_type = group.loc[bottom_idx]['PALTypeChoice']
                if bottom_type != 'kısa ağır':
                    continue
                for j in range(len(group)):
                    if used[j]:
                        continue
                    row = group.loc[j]
                    if row['PALTypeChoice'] == 'kısa hafif' and total_effective + row['EffectivePallet'] <= 33:
                        slots_top[idx] = j
                        used[j] = True
                        total_effective += row['EffectivePallet']
                        assigned_ids.add(j)
                        break

            # 3. kısa hafif → boş alt slotlara
            for idx, slot in enumerate(slots_bottom):
                if slot is None:
                    for j in range(len(group)):
                        if used[j]:
                            continue
                        row = group.loc[j]
                        if row['PALTypeChoice'] == 'kısa hafif' and total_effective + row['EffectivePallet'] <= 33:
                            slots_bottom[idx] = j
                            used[j] = True
                            total_effective += row['EffectivePallet']
                            assigned_ids.add(j)
                            break

            # 4. Gerçek atamayı kaydet (1 defa)
            for idx in assigned_ids:
                row = group.loc[idx].to_dict()
                row['Assigned_Truck'] = truck_id

                if idx in slots_bottom:
                    row['Layer'] = 'bottom'
                elif idx in slots_top:
                    row['Layer'] = 'top'
                else:
                    row['Layer'] = 'unknown'

                assignments.append(row)

            truck_counter += 1

    return pd.DataFrame(assignments)



def plot_truck_grid(df, truck_id):
    df = df[df['Assigned_Truck'] == truck_id].copy()
    df['PALTypeChoice'] = df['PALTypeChoice'].str.lower().str.strip()

    width = 33
    max_stack = 2
    layers = [[''] * width for _ in range(max_stack)]

    colors = {
        'yüksek palet': 'red',
        'kısa ağır': 'blue',
        'kısa hafif': 'green'
    }
    labels = {
        'yüksek palet': 'Y',
        'kısa ağır': 'KA',
        'kısa hafif': 'KH'
    }

    count_map = {'yüksek palet': 0, 'kısa ağır': 0, 'kısa hafif': 0}
    idx = 0

    # Yüksek palet ve kısa ağır paletleri yerleştir
    for _, row in df.iterrows():
        pal_type = row['PALTypeChoice']
        if pal_type not in ['yüksek palet', 'kısa ağır']:
            continue
        if pal_type == 'yüksek palet':
            count = int(round(row['EffectivePallet']))
        else:
            count = int(row['CPallet'])
        count_map[pal_type] += count
        for _ in range(count):
            if idx >= width:
                break
            if pal_type == 'yüksek palet':
                for l in range(max_stack):
                    layers[l][idx] = pal_type
            else:
                layers[0][idx] = pal_type
            idx += 1

    # Kısa hafif paletleri yerleştir (boş olan yerlere)
    for _, row in df.iterrows():
        if row['PALTypeChoice'] != 'kısa hafif':
            continue
        count = int(round(row['CPallet']))
        count_map['kısa hafif'] += count
        placed = 0

        for i in range(width):
            for l in range(max_stack):
                if layers[l][i] == '':
                    layers[l][i] = 'kısa hafif'
                    placed += 1
                    if placed >= count:
                        break
            if placed >= count:
                break

    fig, ax = plt.subplots(figsize=(width, 2.5))

    x = 0
    while x < width:
        top_pal = layers[0][x]
        bottom_pal = layers[1][x]

        if top_pal == 'yüksek palet' and bottom_pal == 'yüksek palet':
            # Yüksek palet çift katman kaplıyor
            rect = plt.Rectangle((x, 0), 1, 2, facecolor=colors[top_pal], edgecolor='black', alpha=0.9)
            ax.add_patch(rect)
            ax.text(x + 0.5, 1, labels[top_pal], ha='center', va='center', fontsize=8, color='white')
            x += 1
            continue
        else:
            if top_pal:
                rect = plt.Rectangle((x, 0), 1, 1, facecolor=colors[top_pal], edgecolor='black', alpha=0.9)
                ax.add_patch(rect)
                ax.text(x + 0.5, 0.5, labels[top_pal], ha='center', va='center', fontsize=8,
                        color='white' if colors[top_pal] != 'white' else 'black')

            if bottom_pal:
                rect = plt.Rectangle((x, 1), 1, 1, facecolor=colors[bottom_pal], edgecolor='black', alpha=0.9)
                ax.add_patch(rect)
                ax.text(x + 0.5, 1.5, labels[bottom_pal], ha='center', va='center', fontsize=8,
                        color='white' if colors[bottom_pal] != 'white' else 'black')

            x += 1

    toplam = sum(count_map.values())
    info_text = f"Y: {count_map['yüksek palet']} | KA: {count_map['kısa ağır']} | KH: {count_map['kısa hafif']} | Toplam: {toplam}"
    ax.text(width / 2, max_stack + 0.2, info_text, ha='center', va='bottom', fontsize=10, fontweight='bold')

    ax.set_xlim(0, width)
    ax.set_ylim(0, max_stack + 0.6)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_aspect('equal')
    ax.set_title(f"{truck_id} - Araç Yükleme Görseli", fontsize=12)
    ax.plot([0, width], [0, 0], color='black', linewidth=2)
    ax.plot([0, width], [max_stack, max_stack], color='black', linewidth=2)
    ax.plot([0, 0], [0, max_stack], color='black', linewidth=2)
    ax.plot([width, width], [0, max_stack], color='black', linewidth=2)

    plt.tight_layout()
    return fig