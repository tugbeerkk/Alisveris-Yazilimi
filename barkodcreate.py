from barcode import ISBN13
import os
from barcode.writer import ImageWriter
import barcode

def createbar(num, name):
    # 1. ISBN13 yerine EAN13 sınıfını çağırıyoruz (869 ile başlayan barkodlar için)
    EAN13 = barcode.get_class('ean13')
    
    # 2. Barkodları static/barcodes klasöründe saklamak daha düzenli olur
    klasor = os.path.join("static", "barcodes")
    os.makedirs(klasor, exist_ok=True)
    
    # Uzantısız dosya yolu (python-barcode sonuna otomatik .png ekler)
    dosya_adi_uzantisiz = os.path.join(klasor, str(name))
    
    # 3. Barkod görselini oluşturup kaydediyoruz
    barkod_nesnesi = EAN13(str(num), writer=ImageWriter())
    kaydedilen_yol = barkod_nesnesi.save(dosya_adi_uzantisiz)
    
    # 4. Veritabanına kaydedilecek göreceli (relative) yolu döndürüyoruz (örn: barcodes/urun_1.png)
    return f"barcodes/{str(name)}.png"

def createbaracodecode(isletme_id, sira_no):
    ulke_kodu = "869"  # Sabit ülke kodu
    
    # isletme_id'yi 4 haneli firma koduna dönüştür (Örn: 5 -> "0005")
    firma_kodu = str(isletme_id).zfill(4)
    
    # Gelen sıra numarasını 5 haneli ürün koduna dönüştür (Örn: 1 -> "00001", 12 -> "00012")
    urun_kodu = str(sira_no).zfill(5)
    
    ilk_12_hane = ulke_kodu + firma_kodu + urun_kodu
    
    # EAN-13 Kontrol Basamağı (13. hane) Hesaplaması
    tek_toplam = sum(int(ilk_12_hane[i]) for i in range(0, 12, 2))
    cift_toplam = sum(int(ilk_12_hane[i]) for i in range(1, 12, 2))
    
    genel_toplam = tek_toplam + (cift_toplam * 3)
    kontrol_basamagi = (10 - (genel_toplam % 10)) % 10
    
    # Tam 13 haneli barkod kodu
    barkod = ilk_12_hane + str(kontrol_basamagi)
    return barkod