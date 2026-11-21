from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database import db, Isletme, Urun, Hatirlatici, Bildirim

hatirlatici_bp = Blueprint('hatirlatici', __name__)


def hatirlatici_kontrol(urun):
    """Stok hatırlatıcı sınırına (veya altına) geldiyse bildirim oluşturur.
    Mesaj döner, uyarı yoksa None."""
    h = urun.hatirlatici
    if not h or h.tetiklendi or urun.stok_miktari > h.esik:
        return None
    mesaj = f"'{urun.urun_adi}' stoğu {urun.stok_miktari} adede düştü (hatırlatıcı: {h.esik})."
    db.session.add(Bildirim(isletme_id=urun.isletme_id, mesaj=mesaj))
    h.tetiklendi = True
    db.session.commit()
    return mesaj


def hepsini_kontrol(isletme_id):
    """İşletmenin tüm hatırlatıcılarını tarar: sınıra gelenler için bildirim üretir,
    stoğu tekrar sınırın üstüne çıkanları yeniden devreye alır."""
    degisti = False
    for h in Hatirlatici.query.filter_by(isletme_id=isletme_id).all():
        urun = h.urun
        if urun.stok_miktari <= h.esik and not h.tetiklendi:
            db.session.add(Bildirim(
                isletme_id=isletme_id,
                mesaj=f"'{urun.urun_adi}' stoğu {urun.stok_miktari} adede düştü (hatırlatıcı: {h.esik})."))
            h.tetiklendi = True
            degisti = True
        elif urun.stok_miktari > h.esik and h.tetiklendi:
            h.tetiklendi = False
            degisti = True
    if degisti:
        db.session.commit()


def bildirim_context():
    """Tüm şablonlarda okunmamış bildirimleri 'bildirimler' adıyla kullanılabilir yapar."""
    if 'isletme_id' not in session:
        return {}
    hepsini_kontrol(session['isletme_id'])   # sayfa açılırken de kontrol et
    liste = Bildirim.query.filter_by(isletme_id=session['isletme_id'], okundu=False) \
                          .order_by(Bildirim.tarih.desc()).all()
    return {'bildirimler': liste}


def _giris_yok():
    if 'isletme_id' not in session:
        flash('Lütfen önce giriş yapın.', 'warning')
        return redirect(url_for('kayit'))
    return None


@hatirlatici_bp.route('/hatirlatici')
def liste():
    yonlendir = _giris_yok()
    if yonlendir:
        return yonlendir
    isletme = db.session.get(Isletme, session['isletme_id'])
    if not isletme:
        session.clear()
        return redirect(url_for('kayit'))
    urunler = Urun.query.filter_by(isletme_id=isletme.isletme_id).order_by(Urun.urun_adi).all()
    hatirlaticilar = {h.urun_id: h for h in Hatirlatici.query.filter_by(isletme_id=isletme.isletme_id)}
    return render_template('hatirlatici.html', isletme=isletme, urunler=urunler, hatirlaticilar=hatirlaticilar)


@hatirlatici_bp.route('/hatirlatici/<int:urun_id>', methods=['POST'])
def kaydet(urun_id):
    yonlendir = _giris_yok()
    if yonlendir:
        return yonlendir
    urun = db.session.get(Urun, urun_id)
    if not urun or urun.isletme_id != session['isletme_id']:
        flash('Ürün bulunamadı.', 'danger')
        return redirect(url_for('hatirlatici.liste'))
    try:
        esik = int(request.form.get('esik', ''))
        if esik < 0:
            raise ValueError
    except ValueError:
        flash('Lütfen 0 veya daha büyük bir sayı girin.', 'danger')
        return redirect(url_for('hatirlatici.liste'))

    h = urun.hatirlatici
    if h:
        h.esik, h.tetiklendi = esik, False
    else:
        db.session.add(Hatirlatici(isletme_id=urun.isletme_id, urun_id=urun.urun_id, esik=esik))
    db.session.commit()

    flash(f"'{urun.urun_adi}' stoğu {esik} adede gelince haber vereceğim.", 'success')
    uyari = hatirlatici_kontrol(urun)   # stok zaten sınırdaysa hemen bildir
    if uyari:
        flash(uyari, 'warning')
    return redirect(url_for('hatirlatici.liste'))


@hatirlatici_bp.route('/hatirlatici-sil/<int:urun_id>')
def sil(urun_id):
    yonlendir = _giris_yok()
    if yonlendir:
        return yonlendir
    h = Hatirlatici.query.filter_by(urun_id=urun_id, isletme_id=session['isletme_id']).first()
    if h:
        db.session.delete(h)
        db.session.commit()
        flash('Hatırlatıcı kaldırıldı.', 'info')
    return redirect(url_for('hatirlatici.liste'))


@hatirlatici_bp.route('/bildirim-okundu/<int:bildirim_id>')
def okundu(bildirim_id):
    yonlendir = _giris_yok()
    if yonlendir:
        return yonlendir
    b = db.session.get(Bildirim, bildirim_id)
    if b and b.isletme_id == session['isletme_id']:
        b.okundu = True
        db.session.commit()
    return redirect(request.referrer or url_for('panel'))


@hatirlatici_bp.route('/bildirim-hepsi-okundu')
def hepsi_okundu():
    yonlendir = _giris_yok()
    if yonlendir:
        return yonlendir
    Bildirim.query.filter_by(isletme_id=session['isletme_id'], okundu=False).update({'okundu': True})
    db.session.commit()
    return redirect(request.referrer or url_for('panel'))
