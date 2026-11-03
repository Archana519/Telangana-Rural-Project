"""One-off patch (kept for provenance): maps handle the 5-facility layer (3 retained + 2 Gram Panchayat HQ points)."""
p = r"D:\Telangana_Rural_Project\src\reporting\make_final_maps.py"
s = open(p, encoding="utf-8").read()


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:90])
    s = s.replace(a, b)


rep('''    zext = (min(fx) - 330, max(fx) + 330, min(fy) - 300, max(fy) + 300)          # main settlement: the three retained facilities plus 300 m''',
    '''    _cx, _cy = float(np.median(fx)), float(np.median(fy))
    _mf = [(p_.x, p_.y) for p_ in fac.geometry if ((p_.x - _cx) ** 2 + (p_.y - _cy) ** 2) ** 0.5 < 1500]
    zext = (min(q[0] for q in _mf) - 330, max(q[0] for q in _mf) + 330, min(q[1] for q in _mf) - 300, max(q[1] for q in _mf) + 300)   # main settlement: facilities within 1.5 km plus 300 m
    inside = lambda g_, e_: e_[0] <= g_.x <= e_[1] and e_[2] <= g_.y <= e_[3]
    is_admin = lambda r_: str(r_.facility_type).startswith("Administrative")''')
rep('''    OFF = {"36181600902": (-175, -48), "36181600903": (-235, 12), "HEALTH_8734223673": (-60, 64)}''',
    '''    OFF = {"36181600902": (-175, -48), "36181600903": (-235, 12), "HEALTH_8734223673": (-60, 64), "GP_DAMARAKUNTA": (60, -70)}''')
rep('''        for r in fac.itertuples():
            ax.scatter([r.geometry.x], [r.geometry.y], marker="*", s=90 if not k else 230, c="#ff1744", edgecolors="w", linewidths=0.8, zorder=10)
            if k:''', '''        for r in fac.itertuples():
            if not inside(r.geometry, ext_):
                continue
            ax.scatter([r.geometry.x], [r.geometry.y], marker="s" if is_admin(r) else "*", s=(60 if not k else 150) if is_admin(r) else (90 if not k else 230), c="#aa00ff" if is_admin(r) else "#ff1744", edgecolors="w", linewidths=0.8, zorder=10)
            if k:''')
rep('''[Line2D([], [], marker="*", color="w", mfc="#ff1744", mec="w", ms=11, label="Priority facility (%d)" % len(fac)), Line2D([], [], color="#00e5ff", lw=1.2, label="TGRAC roads")],''',
    '''[Line2D([], [], marker="*", color="w", mfc="#ff1744", mec="w", ms=11, label="School / health facility (%d)" % sum(not is_admin(r_) for r_ in fac.itertuples())),
                   Line2D([], [], marker="s", color="w", mfc="#aa00ff", mec="w", ms=8, label="Gram Panchayat HQ (TGRAC) (%d)" % sum(is_admin(r_) for r_ in fac.itertuples())), Line2D([], [], color="#00e5ff", lw=1.2, label="TGRAC roads")],''')
rep('''"HEALTH_8734223673": "Sub Centre Damarakunta"}
        OFF5 = {"36181600902": (-190, -52), "36181600903": (-250, 16), "HEALTH_8734223673": (-70, 70)}''',
    '''"HEALTH_8734223673": "Sub Centre Damarakunta", "GP_DAMARAKUNTA": "Damarakunta Gram Panchayat HQ (TGRAC point)"}
        OFF5 = {"36181600902": (-190, -52), "36181600903": (-250, 16), "HEALTH_8734223673": (-70, 70), "GP_DAMARAKUNTA": (70, -80)}''')
rep('''            for fid, rr in names.items():
                lon, lat = TO_LL.transform(rr.geometry.x, rr.geometry.y)
                un = False
                ax.scatter([rr.geometry.x], [rr.geometry.y], marker="*", s=300, c="#ffd600" if not un else "#ff9100", edgecolors="k", linewidths=1.0, zorder=12)
                ax.annotate("%s\\n%.5f°N, %.5f°E%s" % (short[fid], lat, lon, "\\nUNVERIFIED: no footprint within 371 m" if un else ""), (rr.geometry.x, rr.geometry.y), xytext=OFF5[fid], textcoords="offset points",''',
    '''            for fid, rr in names.items():
                if not inside(rr.geometry, zext):
                    continue
                lon, lat = TO_LL.transform(rr.geometry.x, rr.geometry.y)
                adm = is_admin(rr)
                ax.scatter([rr.geometry.x], [rr.geometry.y], marker="s" if adm else "*", s=170 if adm else 300, c="#aa00ff" if adm else "#ffd600", edgecolors="k", linewidths=1.0, zorder=12)
                ax.annotate("%s\\n%.5f°N, %.5f°E" % (short.get(fid, rr.facility_name), lat, lon), (rr.geometry.x, rr.geometry.y), xytext=OFF5.get(fid, (50, -50)), textcoords="offset points",''')
rep('''Line2D([], [], marker="*", color="w", mfc="#ffd600", mec="k", ms=13, label="Priority facility (TGRAC coordinate)")],''',
    '''Line2D([], [], marker="*", color="w", mfc="#ffd600", mec="k", ms=13, label="School / health facility (TGRAC coordinate)"),
                               Line2D([], [], marker="s", color="w", mfc="#aa00ff", mec="k", ms=9, label="Gram Panchayat HQ (TGRAC point)")],''')
rep('''"The anganwadi (unverified coordinate) is excluded from the planning layers and maps at the project owner's request (inputs/EXCLUSIONS.md); the plan serves the 3 retained facilities. Footprints''',
    '''"The anganwadi (unverified coordinate) is excluded at the project owner's request (inputs/EXCLUSIONS.md); the plan serves 5 facilities: 3 school/health points and 2 Gram Panchayat headquarters points (inputs/ADMIN_UTILITIES.md; MeeSeva and ESD centres have no located coordinate and are not included). Footprints''')
open(p, "w", encoding="utf-8").write(s)
print("patched")
