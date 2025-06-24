import pandas as pd

def palet_factor(pal_type):
    if isinstance(pal_type, str) and pal_type.strip().lower() == 'kısa hafif':
        return 0.5
    return 1

def calculate_effective_pallet(row):
    try:
        return row['CPallet'] * palet_factor(row['PALTypeChoice'])
    except Exception:
        return 9999  # aşırı büyük değer ver, hata tespiti kolay olsun

def solve_assignment(order_df):
    order_df = order_df.copy().reset_index(drop=True)

    # Effective Pallet hesapla
    order_df['EffectivePallet'] = order_df.apply(calculate_effective_pallet, axis=1)

    # Gruplama
    grouped = order_df.groupby(['Shipping Point/Receiving Pt', 'Location of the ship-to party'])
    assignments = []
    truck_counter = 1

    for (ship_point, ship_to), group in grouped:
        group = group.sort_values(by='EffectivePallet', ascending=False).reset_index(drop=True)
        used = [False] * len(group)

        while not all(used):
            total = 0
            truck_orders = []
            for i in range(len(group)):
                if not used[i]:
                    pallet = group.loc[i, 'EffectivePallet']
                    if pd.isna(pallet):
                        continue
                    if total + pallet <= 33:
                        total += pallet
                        truck_orders.append(i)
            if not truck_orders:
                break  # hiçbir sipariş atanamadıysa sonsuz döngüye girmesin
            for i in truck_orders:
                order = group.loc[i].to_dict()
                order['Assigned_Truck'] = f"Truck-{truck_counter}"
                assignments.append(order)
                used[i] = True
            truck_counter += 1

    return pd.DataFrame(assignments)
