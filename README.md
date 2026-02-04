# SIF to BLF Converter

Somat eDAQ SIF dosyalarını Vector BLF formatına dönüştürür.

## 🎯 Özellikler

✅ **CAN Interface Desteği**: 3 CAN interface (500 kbps, 250 kbps)  
✅ **Çoklu Sensor**: 36 analog/digital kanal  
✅ **GPS Desteği**: Konum ve hız verileri  
✅ **Vector Uyumlu**: CANalyzer/CANoe ile açılabilir  
✅ **Saf Python**: Harici dependency gerekmez

## 📋 Gereksinimler

- Python 3.7 veya üzeri
- Standart Python kütüphaneleri (başka bir şey gerekmez!)

## 🚀 Kurulum

```bash
# Repository'yi klonla
git clone https://github.com/ontoloji/Sif_to_blf.git
cd Sif_to_blf

# Dosyalar hazır, harici paket kurulumu gerekmez!
```

## 📖 Kullanım

### Temel Kullanım

```bash
python sif_to_blf_converter.py ornek_sif.sif output.blf
```

### Verbose Mod (Detaylı Çıktı)

```bash
python sif_to_blf_converter.py ornek_sif.sif output.blf -v
```

### Yardım

```bash
python sif_to_blf_converter.py --help
```

## 📂 Dosya Yapısı

```
Sif_to_blf/
├── sif_parser.py              # SIF dosyası parser modülü
├── blf_writer.py              # Vector BLF writer modülü
├── sif_to_blf_converter.py   # Ana converter programı
├── requirements.txt           # Paket gereksinimleri (boş)
├── README.md                  # Bu dosya
└── ornek_sif.sif             # Örnek SIF dosyası
```

## 🔍 SIF Dosyası Yapısı

SIF dosyaları şu bölümleri içerir:

1. **Binary Header**: `SoMateDAQPCMDataFile-v1.1`
2. **Metadata (INI Format)**:
   - Sistem konfigürasyonu
   - CAN interface ayarları
   - Sensor kanal tanımları
   - Kalibrasyon verileri
3. **Binary Data**: Ölçüm verileri

## 📊 Desteklenen Veri Tipleri

| Tip | Örnek | Birim |
|-----|-------|-------|
| **Pressure** | CompIn_P, AirDryIn_P | mbar |
| **Temperature** | Amb_T, CompIn_T | °C |
| **Voltage** | IAPU_In_P | mV |
| **GPS Position** | lat, lon, altitude | degrees, m |
| **GPS Speed** | speed_kmh, speed_ms | km/h, m/s |

## 🎓 Örnek Çıktı

```bash
$ python sif_to_blf_converter.py ornek_sif.sif test.blf

🔍 Parsing SIF file: ornek_sif.sif
✅ SIF Version: v3.17.0 build 461
✅ Found 3 CAN interfaces
✅ Found 36 channels
   📡 CAN_1: 500000 bps, DBs: PCAN
   📡 CAN_2: 500000 bps, DBs: PCAN
   📡 CAN_3: 250000 bps, DBs: Foton_CAN1, Foton_CAN2_v2

📊 Channels (showing first 5):
   1. CompIn_P (Pressure) - mbar, 100 Hz
   2. CompOut_P (Pressure) - mbar, 100 Hz
   3. ESS_IAPU41_P (Pressure) - mbar, 100 Hz
   4. AirDryIn_P (Pressure) - mbar, 100 Hz
   5. BrkChmbr_P (Pressure) - mbar, 100 Hz

🔄 Converting to BLF format...
📦 Binary data size: 15,234,567 bytes
⚙️  Generating 1000 sample messages...
💾 Writing BLF file: test.blf
✅ Conversion completed!
📊 Generated 3,000 BLF objects
```

## ⚠️ Önemli Notlar

### Binary Data Format

Bu versiyon SIF binary data formatının **genel yapısını** parse ediyor. Ancak:

- ⚠️ Binary veri kısmı **reverse engineering** gerektiriyor
- ⚠️ Şu anda **örnek CAN mesajları** oluşturuluyor
- ⚠️ Gerçek veri dönüşümü için Somat format dokümantasyonu gerekli

### Geliştirme Yol Haritası

1. **SIF Binary Format Analizi**
   - Farklı SIF dosyalarıyla test
   - Data pattern'leri belirleme
   - Timestamp encoding çözme

2. **Gerçek Veri Dönüşümü**
   - `_convert_data()` fonksiyonunu güncelleme
   - CAN mesajlarını decode etme
   - Sensor verilerini mapping

3. **İyileştirmeler**
   - Multi-threading support
   - Progress bar
   - Error handling

## 🔧 Geliştirme

### Kod Yapısı

**`sif_parser.py`**
- `SIFParser`: Ana parser sınıfı
- `_find_text_end()`: Binary/text boundary bulucu
- `_parse_can_interfaces()`: CAN config parser
- `_parse_channels()`: Sensor kanal parser

**`blf_writer.py`**
- `BLFWriter`: BLF dosyası writer
- `add_can_message()`: CAN mesajı ekleme
- `_write_header()`: BLF header yazma
- `_write_object()`: BLF object yazma

**`sif_to_blf_converter.py`**
- `SIFToBLFConverter`: Ana converter
- `convert()`: Dönüşüm işlemi
- `_convert_data()`: Binary data dönüştürücü (TODO)

### Test Etme

```bash
# Basit test
python sif_to_blf_converter.py ornek_sif.sif test.blf

# Binary data analizi için
python -c "
from sif_parser import SIFParser
parser = SIFParser('ornek_sif.sif')
data = parser.parse()
print(f'CAN Interfaces: {len(data.can_interfaces)}')
print(f'Channels: {len(data.channels)}')
print(f'Data offset: {data.data_offset}')
"
```

## 🤝 Katkıda Bulunma

1. Fork edin
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Commit edin (`git commit -m 'Add some amazing feature'`)
4. Push edin (`git push origin feature/amazing-feature`)
5. Pull Request açın

## 📄 Lisans

MIT License - Detaylar için `LICENSE` dosyasına bakın.

## 👤 İletişim

- **Repository**: [ontoloji/Sif_to_blf](https://github.com/ontoloji/Sif_to_blf)
- **Issues**: [GitHub Issues](https://github.com/ontoloji/Sif_to_blf/issues)

## 🙏 Teşekkürler

- Somat (HBM) - SIF format için
- Vector - BLF format spesifikasyonu için
- Python Community

---

⭐ Bu projeyi faydalı bulduysanız yıldız vermeyi unutmayın!