# -*- coding: utf-8 -*-
"""Pet Freedom — agency-inquiry DRAFTER (OPTIONAL module; off by default via config.inquiries.enabled).

FILE-BASED: works WITHOUT the companion plugin. Scans data/jurisdictions/*.json and, for every
jurisdiction that still has an OPEN question AND a usable agency contact, drafts a written inquiry
IN THE JURISDICTION'S LEGAL LANGUAGE and writes it to the local queue at data/inquiries.json
(gitignored). Nothing is ever sent here — that's skill/mail.py.

A jurisdiction is "open" when any activity in config.activities has needs_verification==true OR a
status in {"unknown", "unregulated_unclear"}.

Channels:
  - "email"    : the contact has an email -> auto-sendable by skill/mail.py (after you approve it).
  - "web_form" : the contact has only a form_url -> we supply the prefilled text + the URL; submit by hand.

Contact selection (pick_contact): an explicit "primary": true contact wins, using ITS OWN channel
(so we target the authoritative agency even when it only has a web form and a different contact has an
email). We NEVER invent an address — only emails/form_urls present in verified contacts[] are used. A
jurisdiction with an open question but no usable contact is reported as "open but no contact"; we draft
nothing for it.

OPSEC: no owner name/email/domain/species literals live here. The species framing comes from
config.species (latin / common / counterpart); the four questions from config.activities; the signature
from config.inquiries (sender_name / brand_line / public_email). If sender_name is empty, the signature
leaves a clear "[Your name]" placeholder. The from-address used to actually send is read from .env at
runtime by skill/mail.py.

Re-drafts are non-destructive: any human-set status / sent_at / reply already in data/inquiries.json is
preserved across re-drafts (keyed by jurisdiction_id::agency).

CLI:
  python skill/inquiries.py            # re-draft the queue, print how many drafted / open-without-contact
"""
import os
import sys
import glob
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    sys.stdout.reconfigure(encoding="utf-8")  # py3.7+: keep non-ASCII subjects/bodies printable
except Exception:
    pass
import config  # noqa: E402

# Activity status values that count as an unresolved (open) answer.
OPEN_STATUSES = {"unknown", "unregulated_unclear"}

# Localized country/region display name keyed by the jurisdiction's ENGLISH name. Used only for nicer
# salutations; falls back to the English jurisdiction name when absent. (Names only — no species/owner data.)
LOCAL_NAME = {
    "Germany": "Deutschland", "Austria": "Österreich", "Switzerland": "Schweiz",
    "Netherlands": "Nederland", "Belgium": "België", "Japan": "日本",
    "Greece": "Ελλάδα", "Romania": "România", "Russia": "Россия", "Slovakia": "Slovensko",
    "Turkey": "Türkiye", "Vietnam": "Việt Nam", "Spain": "España", "France": "France",
    "Italy": "Italia", "Portugal": "Portugal", "Poland": "Polska", "Czechia": "Česko",
    "Czech Republic": "Česko", "Indonesia": "Indonesia",
}

# ── Localized templates (scrubbed of any owner signature; signature comes from config) ──
#
# Each language provides the fixed sentence frames plus one question phrasing per activity. The species
# framing uses {species} (latin), {common} (primary common name), and {counterpart} (the closely-related
# commonly-kept species clause, or "" when config has no counterpart). Question keys mirror the standard
# config.activities ("keep" / "breed" / "sell_give" / "transport"); a jurisdiction with non-standard
# activities still drafts — any activity without a localized phrasing falls back to the English phrasing,
# and a language with no template at all falls back to English (with a note).
LANG = {
    "en": {
        "subject": "Legal status of keeping pet {common} ({species}) in {name}",
        "greeting": "Dear {agency},",
        "intro": ("I am researching the legal status of keeping domesticated {common} ({species}) as pets, "
                  "in order to publish an accurate, source-cited educational guide for {name}. These animals "
                  "are captive-bred and selectively bred for tameness and kept as pets; they are not "
                  "wild-caught.{counterpart}"),
        "leadin": "Could you please confirm, for {name}:",
        "closing": ("If possible, please point me to the specific statute or rule, and reply in writing so "
                    "that I can cite it accurately. Thank you very much for your time and help."),
        "signoff": "Best regards,",
        "counterpart": (" Note that {species} is a different species from the common domestic pet "
                        "{cp_common} ({cp_latin})."),
        "q": {
            "keep": "Is it legal to KEEP a captive-bred {species} as a pet? Is any permit or registration required?",
            "breed": "Is it legal to BREED them? Is any license required?",
            "sell_give": "Is it legal to SELL or GIVE them to others? Is any dealer license required?",
            "transport": "What is required to TRANSPORT or IMPORT them (for example, a health certificate or permit)?",
        },
    },
    "nl": {
        "subject": "Wettelijke status van het houden van {common} ({species}) als huisdier in {name}",
        "greeting": "Geachte heer/mevrouw,",
        "intro": ("Ik doe onderzoek naar de wettelijke status van het houden van gedomesticeerde {common} "
                  "({species}) als huisdier, om een nauwkeurige, met bronnen onderbouwde voorlichtingsgids "
                  "voor {name} te publiceren. Deze dieren zijn in gevangenschap gefokt en geselecteerd op "
                  "tamheid en worden als huisdier gehouden; ze zijn niet in het wild gevangen.{counterpart}"),
        "leadin": "Zou u voor {name} kunnen bevestigen:",
        "closing": ("Indien mogelijk, verwijs mij naar de specifieke wet of regeling, en antwoord schriftelijk "
                    "zodat ik het correct kan citeren. Hartelijk dank voor uw tijd en hulp."),
        "signoff": "Met vriendelijke groet,",
        "counterpart": (" Let op: {species} is een andere soort dan het gewone tamme huisdier {cp_common} "
                        "({cp_latin})."),
        "q": {
            "keep": "Is het toegestaan om een in gevangenschap gefokte {species} als huisdier te HOUDEN? Is daarvoor een vergunning of registratie nodig?",
            "breed": "Is het toegestaan om ze te FOKKEN? Is daarvoor een vergunning nodig?",
            "sell_give": "Is het toegestaan om ze te VERKOPEN of weg te GEVEN? Is daarvoor een handelsvergunning nodig?",
            "transport": "Wat is vereist om ze te VERVOEREN of te IMPORTEREN (bijvoorbeeld een gezondheidscertificaat of vergunning)?",
        },
    },
    "de": {
        "subject": "Rechtlicher Status der Haltung von {common} ({species}) als Haustier in {name}",
        "greeting": "Sehr geehrte Damen und Herren,",
        "intro": ("Ich recherchiere den rechtlichen Status der Haltung domestizierter {common} ({species}) "
                  "als Haustier, um einen genauen, mit Quellen belegten Ratgeber für {name} zu "
                  "veröffentlichen. Diese Tiere sind in Gefangenschaft gezüchtet und auf Zahmheit "
                  "selektiert und werden als Haustiere gehalten; sie sind nicht wildgefangen.{counterpart}"),
        "leadin": "Könnten Sie für {name} bitte bestätigen:",
        "closing": ("Bitte verweisen Sie nach Möglichkeit auf das konkrete Gesetz oder die Verordnung und "
                    "antworten Sie schriftlich, damit ich es korrekt zitieren kann. Vielen Dank für Ihre "
                    "Zeit und Hilfe."),
        "signoff": "Mit freundlichen Grüßen,",
        "counterpart": (" Hinweis: {species} ist eine andere Art als das gewöhnliche Heimtier {cp_common} "
                        "({cp_latin})."),
        "q": {
            "keep": "Ist es erlaubt, eine in Gefangenschaft gezüchtete {species} als Haustier zu HALTEN? Ist dafür eine Genehmigung oder Registrierung erforderlich?",
            "breed": "Ist es erlaubt, sie zu ZÜCHTEN? Ist dafür eine Erlaubnis erforderlich?",
            "sell_give": "Ist es erlaubt, sie zu VERKAUFEN oder ABZUGEBEN? Ist dafür eine Erlaubnis erforderlich?",
            "transport": "Was ist für den TRANSPORT oder IMPORT erforderlich (z. B. ein Gesundheitszeugnis oder eine Genehmigung)?",
        },
    },
    "fr": {
        "subject": "Statut juridique de la détention de {common} ({species}) comme animal de compagnie ({name})",
        "greeting": "Madame, Monsieur,",
        "intro": ("Je réalise une recherche sur le statut juridique de la détention de {common} domestiques "
                  "({species}) comme animaux de compagnie, afin de publier un guide pédagogique précis et "
                  "sourcé pour {name}. Ces animaux sont nés et élevés en captivité, sélectionnés pour leur "
                  "docilité et gardés comme animaux de compagnie; ils ne sont pas capturés dans la "
                  "nature.{counterpart}"),
        "leadin": "Pourriez-vous confirmer, pour {name} :",
        "closing": ("Si possible, veuillez m'indiquer la loi ou le règlement précis et répondre par écrit afin "
                    "que je puisse le citer correctement. Je vous remercie sincèrement de votre temps et de "
                    "votre aide."),
        "signoff": "Cordialement,",
        "counterpart": (" À noter : {species} est une espèce différente de l'animal de compagnie domestique "
                        "courant, {cp_common} ({cp_latin})."),
        "q": {
            "keep": "Est-il légal de DÉTENIR un {species} né en captivité comme animal de compagnie ? Un permis ou un enregistrement est-il requis ?",
            "breed": "Est-il légal de les ÉLEVER (reproduction) ? Un permis est-il requis ?",
            "sell_give": "Est-il légal de les VENDRE ou de les DONNER à autrui ? Un permis de commerçant est-il requis ?",
            "transport": "Que faut-il pour les TRANSPORTER ou les IMPORTER (par exemple un certificat sanitaire ou un permis) ?",
        },
    },
    "es": {
        "subject": "Estatus legal de la tenencia de {common} ({species}) como mascota en {name}",
        "greeting": "Estimados señores:",
        "intro": ("Estoy investigando el estatus legal de la tenencia de {common} domésticos ({species}) como "
                  "mascotas, con el fin de publicar una guía educativa precisa y con fuentes para {name}. "
                  "Estos animales nacen y se crían en cautiverio, se seleccionan por su docilidad y se "
                  "mantienen como mascotas; no son capturados en la naturaleza.{counterpart}"),
        "leadin": "¿Podrían confirmar, para {name}:",
        "closing": ("Si es posible, indíquenme la ley o el reglamento específico y respondan por escrito "
                    "para poder citarlo con exactitud. Muchas gracias por su tiempo y ayuda."),
        "signoff": "Atentamente,",
        "counterpart": (" Nota: {species} es una especie distinta de la mascota doméstica común {cp_common} "
                        "({cp_latin})."),
        "q": {
            "keep": "¿Es legal TENER un {species} criado en cautiverio como mascota? ¿Se requiere algún permiso o registro?",
            "breed": "¿Es legal CRIARLOS (reproducción)? ¿Se requiere algún permiso?",
            "sell_give": "¿Es legal VENDERLOS o REGALARLOS a otras personas? ¿Se requiere una licencia de comerciante?",
            "transport": "¿Qué se requiere para TRANSPORTARLOS o IMPORTARLOS (por ejemplo, un certificado sanitario o un permiso)?",
        },
    },
    "ja": {
        "subject": "{name}における{common}（{species}）のペット飼育の法的地位について",
        "greeting": "ご担当者様",
        "intro": ("私は、ペットとして飼育される家畜化された{common}（{species}）の法的地位について調査し、"
                  "正確で出典に基づく教育的なガイドを{name}向けに公開するために情報を集めています。"
                  "これらの個体は繁殖施設で生まれ、温和さを選抜して育てられたペットであり、"
                  "野生捕獲ではありません。{counterpart}"),
        "leadin": "{name}について、以下の点をご確認いただけますでしょうか：",
        "closing": ("可能であれば、該当する法律や規則をお示しいただき、正確に引用できるよう書面で"
                    "ご回答いただけますと幸いです。お時間をいただきありがとうございます。"),
        "signoff": "よろしくお願いいたします。",
        "counterpart": ("なお、{species}は一般的なペットの{cp_common}（{cp_latin}）とは異なる種です。"),
        "q": {
            "keep": "繁殖個体の{species}をペットとして飼育することは合法ですか。許可や登録は必要ですか。",
            "breed": "繁殖させることは合法ですか。許可は必要ですか。",
            "sell_give": "他者へ販売または譲渡することは合法ですか。販売業の許可は必要ですか。",
            "transport": "輸送または輸入には何が必要ですか（例：健康証明書や許可）。",
        },
    },
    "it": {
        "subject": "Stato giuridico della detenzione di {common} ({species}) come animale da compagnia in {name}",
        "greeting": "Gentili Signore e Signori,",
        "intro": ("Sto svolgendo una ricerca sullo stato giuridico della detenzione di {common} domestici "
                  "({species}) come animali da compagnia, al fine di pubblicare una guida divulgativa "
                  "accurata e documentata per {name}. Questi animali nascono e sono allevati in cattività, "
                  "selezionati per la docilità e tenuti come animali da compagnia; non sono catturati in "
                  "natura.{counterpart}"),
        "leadin": "Potreste cortesemente confermare, per {name}:",
        "closing": ("Se possibile, vi prego di indicarmi la legge o il regolamento specifico e di rispondere "
                    "per iscritto, così da poterlo citare correttamente. Vi ringrazio molto per il vostro "
                    "tempo e il vostro aiuto."),
        "signoff": "Cordiali saluti,",
        "counterpart": (" Nota: {species} è una specie diversa dal comune animale da compagnia domestico "
                        "{cp_common} ({cp_latin})."),
        "q": {
            "keep": "È legale DETENERE un {species} nato in cattività come animale da compagnia? È richiesto un permesso o una registrazione?",
            "breed": "È legale ALLEVARLI (riproduzione)? È richiesto un permesso?",
            "sell_give": "È legale VENDERLI o CEDERLI ad altri? È richiesta una licenza di commerciante?",
            "transport": "Cosa è necessario per TRASPORTARLI o IMPORTARLI (ad esempio un certificato sanitario o un permesso)?",
        },
    },
    "pt": {
        "subject": "Estatuto jurídico da detenção de {common} ({species}) como animal de companhia em {name}",
        "greeting": "Exmos. Senhores,",
        "intro": ("Encontro-me a investigar o estatuto jurídico da detenção de {common} domésticos ({species}) "
                  "como animais de companhia, a fim de publicar um guia educativo rigoroso e com fontes para "
                  "{name}. Estes animais nascem e são criados em cativeiro, selecionados pela docilidade e "
                  "mantidos como animais de companhia; não são capturados na natureza.{counterpart}"),
        "leadin": "Poderiam confirmar, para {name}:",
        "closing": ("Se possível, indiquem-me a lei ou o regulamento específico e respondam por escrito para "
                    "que eu o possa citar com exatidão. Muito obrigado pelo vosso tempo e ajuda."),
        "signoff": "Com os melhores cumprimentos,",
        "counterpart": (" Nota: {species} é uma espécie diferente do animal de companhia doméstico comum "
                        "{cp_common} ({cp_latin})."),
        "q": {
            "keep": "É legal DETER um {species} criado em cativeiro como animal de companhia? É necessária alguma licença ou registo?",
            "breed": "É legal CRIÁ-LOS (reprodução)? É necessária alguma licença?",
            "sell_give": "É legal VENDÊ-LOS ou DOÁ-LOS a terceiros? É necessária licença de comerciante?",
            "transport": "O que é necessário para os TRANSPORTAR ou IMPORTAR (por exemplo, um certificado sanitário ou licença)?",
        },
    },
    "pl": {
        "subject": "Status prawny utrzymywania {common} ({species}) jako zwierzęcia domowego w {name}",
        "greeting": "Szanowni Państwo,",
        "intro": ("Prowadzę badanie statusu prawnego utrzymywania udomowionych {common} ({species}) jako "
                  "zwierząt domowych, w celu opublikowania rzetelnego, opartego na źródłach przewodnika dla "
                  "{name}. Zwierzęta te pochodzą z hodowli w niewoli, są selekcjonowane pod kątem łagodności "
                  "i trzymane jako zwierzęta domowe; nie są chwytane w naturze.{counterpart}"),
        "leadin": "Czy mogliby Państwo potwierdzić dla {name}:",
        "closing": ("W miarę możliwości proszę o wskazanie konkretnej ustawy lub rozporządzenia oraz o "
                    "odpowiedź na piśmie, abym mógł je dokładnie zacytować. Bardzo dziękuję za poświęcony "
                    "czas i pomoc."),
        "signoff": "Z wyrazami szacunku,",
        "counterpart": (" Uwaga: {species} to inny gatunek niż popularne zwierzę domowe {cp_common} "
                        "({cp_latin})."),
        "q": {
            "keep": "Czy legalne jest UTRZYMYWANIE {species} pochodzącego z hodowli jako zwierzęcia domowego? Czy wymagane jest zezwolenie lub rejestracja?",
            "breed": "Czy legalne jest ich ROZMNAŻANIE (hodowla)? Czy wymagane jest zezwolenie?",
            "sell_give": "Czy legalna jest ich SPRZEDAŻ lub nieodpłatne PRZEKAZANIE innym? Czy wymagane jest zezwolenie na handel?",
            "transport": "Co jest wymagane do ich TRANSPORTU lub IMPORTU (np. świadectwo zdrowia lub zezwolenie)?",
        },
    },
    "cs": {
        "subject": "Právní status chovu {common} ({species}) jako domácího mazlíčka v {name}",
        "greeting": "Vážení,",
        "intro": ("Zkoumám právní status chovu domestikovaných {common} ({species}) jako domácích mazlíčků, "
                  "abych vydal přesného, zdroji podloženého průvodce pro {name}. Tato zvířata se rodí a jsou "
                  "odchovávána v zajetí, jsou selektována na krotkost a chována jako domácí mazlíčci; nejsou "
                  "odchytávána ve volné přírodě.{counterpart}"),
        "leadin": "Mohli byste pro {name} potvrdit:",
        "closing": ("Pokud možno mi prosím uveďte konkrétní zákon nebo vyhlášku a odpovězte písemně, abych "
                    "je mohl přesně citovat. Velmi děkuji za váš čas a pomoc."),
        "signoff": "S pozdravem,",
        "counterpart": (" Poznámka: {species} je jiný druh než běžné domácí zvíře {cp_common} ({cp_latin})."),
        "q": {
            "keep": "Je legální CHOVAT {species} odchovaného v zajetí jako domácího mazlíčka? Je vyžadováno povolení nebo registrace?",
            "breed": "Je legální je ROZMNOŽOVAT (chov)? Je vyžadováno povolení?",
            "sell_give": "Je legální je PRODÁVAT nebo DAROVAT jiným? Je vyžadována obchodní licence?",
            "transport": "Co je potřeba k jejich PŘEPRAVĚ nebo DOVOZU (například veterinární osvědčení nebo povolení)?",
        },
    },
    "el": {
        "subject": "Νομικό καθεστώς της διατήρησης {common} ({species}) ως κατοικιδίου στην {name}",
        "greeting": "Αξιότιμοι κύριοι/κυρίες,",
        "intro": ("Διεξάγω έρευνα σχετικά με το νομικό καθεστώς της διατήρησης εξημερωμένων {common} "
                  "({species}) ως κατοικιδίων ζώων, με σκοπό να δημοσιεύσω έναν ακριβή, τεκμηριωμένο με πηγές "
                  "εκπαιδευτικό οδηγό για την {name}. Τα ζώα αυτά γεννιούνται και εκτρέφονται σε αιχμαλωσία, "
                  "επιλέγονται για την πραότητά τους και διατηρούνται ως κατοικίδια· δεν συλλαμβάνονται από τη "
                  "φύση.{counterpart}"),
        "leadin": "Θα μπορούσατε να επιβεβαιώσετε, για την {name}:",
        "closing": ("Εάν είναι δυνατόν, παρακαλώ υποδείξτε μου τον συγκεκριμένο νόμο ή κανονισμό και απαντήστε "
                    "εγγράφως, ώστε να μπορώ να τον παραθέσω με ακρίβεια. Σας ευχαριστώ θερμά για τον χρόνο και "
                    "τη βοήθειά σας."),
        "signoff": "Με εκτίμηση,",
        "counterpart": (" Σημείωση: το {species} είναι διαφορετικό είδος από το κοινό οικόσιτο κατοικίδιο "
                        "{cp_common} ({cp_latin})."),
        "q": {
            "keep": "Είναι νόμιμο να ΔΙΑΤΗΡΕΙ κανείς έναν {species} γεννημένο σε αιχμαλωσία ως κατοικίδιο; Απαιτείται άδεια ή καταχώριση;",
            "breed": "Είναι νόμιμη η ΑΝΑΠΑΡΑΓΩΓΗ τους; Απαιτείται άδεια;",
            "sell_give": "Είναι νόμιμο να τους ΠΩΛΕΙ ή να τους ΧΑΡΙΖΕΙ κανείς σε άλλους; Απαιτείται άδεια εμπόρου;",
            "transport": "Τι απαιτείται για τη ΜΕΤΑΦΟΡΑ ή την ΕΙΣΑΓΩΓΗ τους (για παράδειγμα, υγειονομικό πιστοποιητικό ή άδεια);",
        },
    },
    "id": {
        "subject": "Status hukum pemeliharaan {common} ({species}) sebagai hewan peliharaan di {name}",
        "greeting": "Kepada Yth. Bapak/Ibu,",
        "intro": ("Saya sedang meneliti status hukum pemeliharaan {common} domestik ({species}) sebagai hewan "
                  "peliharaan, untuk menerbitkan panduan edukatif yang akurat dan bersumber bagi {name}. "
                  "Hewan-hewan ini lahir dan dibesarkan di penangkaran, diseleksi untuk kejinakan, dan "
                  "dipelihara sebagai hewan peliharaan; bukan hasil tangkapan dari alam liar.{counterpart}"),
        "leadin": "Mohon konfirmasi, untuk {name}:",
        "closing": ("Jika memungkinkan, mohon tunjukkan undang-undang atau peraturan spesifiknya, dan mohon "
                    "jawaban secara tertulis agar dapat saya kutip dengan akurat. Terima kasih banyak atas waktu "
                    "dan bantuan Anda."),
        "signoff": "Hormat saya,",
        "counterpart": (" Catatan: {species} adalah spesies yang berbeda dari hewan peliharaan umum "
                        "{cp_common} ({cp_latin})."),
        "q": {
            "keep": "Apakah legal MEMELIHARA {species} hasil penangkaran sebagai hewan peliharaan? Apakah diperlukan izin atau registrasi?",
            "breed": "Apakah legal MENGEMBANGBIAKKAN mereka? Apakah diperlukan izin?",
            "sell_give": "Apakah legal MENJUAL atau MEMBERIKAN mereka kepada orang lain? Apakah diperlukan izin pedagang?",
            "transport": "Apa yang diperlukan untuk MENGANGKUT atau MENGIMPOR mereka (misalnya sertifikat kesehatan atau izin)?",
        },
    },
    "ro": {
        "subject": "Statutul juridic al deținerii {common} ({species}) ca animal de companie în {name}",
        "greeting": "Stimată doamnă/Stimate domn,",
        "intro": ("Realizez o cercetare privind statutul juridic al deținerii {common} domestici ({species}) "
                  "ca animale de companie, în scopul publicării unui ghid educativ precis și documentat pentru "
                  "{name}. Aceste animale sunt născute și crescute în captivitate, selectate pentru blândețe "
                  "și ținute ca animale de companie; nu sunt capturate din natură.{counterpart}"),
        "leadin": "Ați putea confirma, pentru {name}:",
        "closing": ("Dacă este posibil, vă rog să îmi indicați legea sau reglementarea specifică și să răspundeți "
                    "în scris, pentru a o putea cita cu exactitate. Vă mulțumesc foarte mult pentru timpul și "
                    "ajutorul dumneavoastră."),
        "signoff": "Cu stimă,",
        "counterpart": (" Notă: {species} este o specie diferită de animalul de companie domestic comun "
                        "{cp_common} ({cp_latin})."),
        "q": {
            "keep": "Este legal să DEȚII un {species} născut în captivitate ca animal de companie? Este necesară o autorizație sau înregistrare?",
            "breed": "Este legal să îi ÎNMULȚEȘTI (reproducere)? Este necesară o autorizație?",
            "sell_give": "Este legal să îi VINZI sau să îi DĂRUIEȘTI altora? Este necesară o licență de comerciant?",
            "transport": "Ce este necesar pentru a-i TRANSPORTA sau IMPORTA (de exemplu, un certificat sanitar sau o autorizație)?",
        },
    },
    "ru": {
        "subject": "Правовой статус содержания {common} ({species}) в качестве домашнего питомца в {name}",
        "greeting": "Уважаемые господа,",
        "intro": ("Я изучаю правовой статус содержания одомашненных {common} ({species}) в качестве домашних "
                  "питомцев с целью публикации точного и основанного на источниках образовательного "
                  "руководства для {name}. Эти животные рождены и выращены в неволе, отобраны за их кротость и "
                  "содержатся как питомцы; они не выловлены в дикой природе.{counterpart}"),
        "leadin": "Не могли бы вы подтвердить для {name}:",
        "closing": ("По возможности укажите, пожалуйста, конкретный закон или нормативный акт и ответьте "
                    "письменно, чтобы я мог точно его процитировать. Большое спасибо за ваше время и помощь."),
        "signoff": "С уважением,",
        "counterpart": (" Примечание: {species} — это иной вид, нежели обычный домашний питомец {cp_common} "
                        "({cp_latin})."),
        "q": {
            "keep": "Законно ли СОДЕРЖАТЬ выведенного в неволе {species} в качестве домашнего питомца? Требуется ли разрешение или регистрация?",
            "breed": "Законно ли их РАЗВОДИТЬ? Требуется ли разрешение?",
            "sell_give": "Законно ли их ПРОДАВАТЬ или ДАРИТЬ другим? Требуется ли лицензия торговца?",
            "transport": "Что требуется для их ПЕРЕВОЗКИ или ВВОЗА (например, ветеринарный сертификат или разрешение)?",
        },
    },
    "sk": {
        "subject": "Právny stav chovu {common} ({species}) ako domáceho zvieraťa v {name}",
        "greeting": "Vážené dámy a páni,",
        "intro": ("Skúmam právny stav chovu domestikovaných {common} ({species}) ako domácich zvierat s cieľom "
                  "vydať presného, zdrojmi podloženého vzdelávacieho sprievodcu pre {name}. Tieto zvieratá sa "
                  "rodia a sú odchovávané v zajatí, sú selektované na krotkosť a chované ako domáce zvieratá; "
                  "nie sú odchytené vo voľnej prírode.{counterpart}"),
        "leadin": "Mohli by ste pre {name} potvrdiť:",
        "closing": ("Ak je to možné, uveďte mi prosím konkrétny zákon alebo predpis a odpovedzte písomne, aby "
                    "som ho mohol presne citovať. Veľmi pekne ďakujem za váš čas a pomoc."),
        "signoff": "S pozdravom,",
        "counterpart": (" Poznámka: {species} je iný druh než bežné domáce zviera {cp_common} ({cp_latin})."),
        "q": {
            "keep": "Je legálne CHOVAŤ {species} odchovaného v zajatí ako domáce zviera? Vyžaduje sa povolenie alebo registrácia?",
            "breed": "Je legálne ich ROZMNOŽOVAŤ (chov)? Vyžaduje sa povolenie?",
            "sell_give": "Je legálne ich PREDÁVAŤ alebo DAROVAŤ iným? Vyžaduje sa obchodná licencia?",
            "transport": "Čo je potrebné na ich PREPRAVU alebo DOVOZ (napríklad veterinárne osvedčenie alebo povolenie)?",
        },
    },
    "tr": {
        "subject": "{common} ({species}) hayvanının {name} ülkesinde evcil hayvan olarak bulundurulmasının yasal durumu",
        "greeting": "Sayın Yetkili,",
        "intro": ("Evcilleştirilmiş {common} ({species}) hayvanlarının evcil hayvan olarak bulundurulmasının "
                  "yasal durumunu araştırıyor ve {name} için doğru, kaynak gösterilmiş eğitici bir rehber "
                  "yayımlamayı amaçlıyorum. Bu hayvanlar esaret altında doğup büyütülür, uysallık için seçilir "
                  "ve evcil hayvan olarak beslenir; doğadan yakalanmazlar.{counterpart}"),
        "leadin": "{name} için lütfen şunları teyit edebilir misiniz:",
        "closing": ("Mümkünse ilgili kanun veya yönetmeliği belirtmenizi ve doğru şekilde alıntılayabilmem için "
                    "yazılı olarak yanıt vermenizi rica ederim. Zaman ayırdığınız ve yardımınız için çok teşekkür "
                    "ederim."),
        "signoff": "Saygılarımla,",
        "counterpart": (" Not: {species}, yaygın evcil hayvan {cp_common} ({cp_latin}) türünden farklı bir türdür."),
        "q": {
            "keep": "Esaret altında üretilmiş bir {species} hayvanını evcil hayvan olarak BULUNDURMAK yasal mıdır? Herhangi bir izin veya kayıt gerekir mi?",
            "breed": "Onları ÜRETMEK (çoğaltmak) yasal mıdır? İzin gerekir mi?",
            "sell_give": "Onları başkalarına SATMAK veya VERMEK yasal mıdır? Satıcı ruhsatı gerekir mi?",
            "transport": "Onları TAŞIMAK veya İTHAL ETMEK için ne gereklidir (örneğin sağlık sertifikası veya izin)?",
        },
    },
    "vi": {
        "subject": "Tình trạng pháp lý của việc nuôi {common} ({species}) làm thú cưng tại {name}",
        "greeting": "Kính gửi Quý cơ quan,",
        "intro": ("Tôi đang nghiên cứu tình trạng pháp lý của việc nuôi {common} thuần hóa ({species}) làm thú "
                  "cưng, nhằm xuất bản một cẩm nang giáo dục chính xác, có trích dẫn nguồn cho {name}. Những con "
                  "vật này được sinh ra và nuôi trong điều kiện nuôi nhốt, được chọn lọc vì sự thuần tính và "
                  "được nuôi làm thú cưng; chúng không bị bắt từ tự nhiên.{counterpart}"),
        "leadin": "Đối với {name}, Quý cơ quan có thể xác nhận giúp:",
        "closing": ("Nếu có thể, xin vui lòng chỉ rõ điều luật hoặc quy định cụ thể và trả lời bằng văn bản để "
                    "tôi có thể trích dẫn chính xác. Xin chân thành cảm ơn thời gian và sự giúp đỡ của Quý cơ quan."),
        "signoff": "Trân trọng,",
        "counterpart": (" Lưu ý: {species} là một loài khác với thú cưng thông thường {cp_common} ({cp_latin})."),
        "q": {
            "keep": "Việc NUÔI một con {species} sinh sản trong điều kiện nuôi nhốt làm thú cưng có hợp pháp không? Có cần giấy phép hoặc đăng ký nào không?",
            "breed": "Việc NHÂN GIỐNG chúng có hợp pháp không? Có cần giấy phép không?",
            "sell_give": "Việc BÁN hoặc CHO TẶNG chúng cho người khác có hợp pháp không? Có cần giấy phép kinh doanh không?",
            "transport": "Cần những gì để VẬN CHUYỂN hoặc NHẬP KHẨU chúng (ví dụ: giấy chứng nhận sức khỏe hoặc giấy phép)?",
        },
    },
}


def is_open(act):
    """An activity record is OPEN if it needs verification or has an unresolved status."""
    if not isinstance(act, dict):
        return True  # malformed -> treat as open to be safe
    if act.get("needs_verification"):
        return True
    return (act.get("status") or "").strip().lower() in OPEN_STATUSES


def pick_contact(contacts):
    """Choose the contact to address + the channel. Returns (contact_dict, channel) or (None, None).

    An explicit primary:true contact wins, using ITS OWN channel (email preferred over its form). Otherwise
    the first contact with an email, then the first with a form_url. We never synthesize an address — only
    values present in the verified contacts[] are returned.
    """
    contacts = [c for c in (contacts or []) if isinstance(c, dict)]
    prim = next((c for c in contacts if c.get("primary")), None)
    if prim:
        if (prim.get("email") or "").strip():
            return prim, "email"
        if (prim.get("form_url") or "").strip():
            return prim, "web_form"
    for c in contacts:
        if (c.get("email") or "").strip():
            return c, "email"
    for c in contacts:
        if (c.get("form_url") or "").strip():
            return c, "web_form"
    return None, None


def _signature(cfg):
    """Build the closing signature from config.inquiries — never a hard-coded real name.

    Lines: sender_name (or a clear placeholder if empty) + optional brand_line + optional public_email.
    """
    inq = cfg.inquiries or {}
    name = (inq.get("sender_name") or "").strip() or "[Your name]"
    lines = [name]
    brand = (inq.get("brand_line") or "").strip()
    if brand:
        lines.append(brand)
    pub = (inq.get("public_email") or "").strip()
    if pub:
        lines.append(pub)
    return "\n".join(lines)


def _species_fields(cfg):
    """The {species}/{common}/{counterpart} substitutions, all sourced from config (no literals)."""
    species = cfg.species_latin or "the species"
    common = cfg.species_common or species
    return species, common


def _counterpart_clause(cfg, t, species, common):
    """Render the localized counterpart sentence, or '' when config has no counterpart."""
    cp = cfg.counterpart
    if not cp:
        return ""
    cp_latin = (cp.get("latin") or "").strip()
    cp_common_list = cp.get("common") or []
    cp_common = (cp_common_list[0] if cp_common_list else cp_latin).strip()
    if not cp_latin and not cp_common:
        return ""
    return t.get("counterpart", "").format(
        species=species, common=common,
        cp_common=cp_common or cp_latin, cp_latin=cp_latin or cp_common)


def draft(cfg, d, lang, agency, open_acts, focus):
    """Compose (subject, body, note) for one open jurisdiction in its legal language.

    open_acts is the ordered list of OPEN activity keys (from config.activities). Questions use the
    language's phrasing where available, else the English phrasing for that activity.
    """
    jur = d.get("jurisdiction") or {}
    name = LOCAL_NAME.get(jur.get("name", ""), jur.get("name", ""))
    t = LANG.get(lang, LANG["en"])
    en = LANG["en"]
    species, common = _species_fields(cfg)
    counterpart = _counterpart_clause(cfg, t, species, common)

    def question(k):
        return t["q"].get(k) or en["q"].get(k) or k
    qs = "\n".join("  - %s" % question(k).format(species=species, common=common) for k in open_acts)

    fields = dict(name=name, agency=agency, species=species, common=common, counterpart=counterpart)
    focus_para = ("\n\n" + focus) if focus else ""
    body = (
        "%s\n\n"
        "%s\n\n"
        "%s\n%s%s\n\n"
        "%s\n\n%s\n%s"
    ) % (
        t["greeting"].format(**fields),
        t["intro"].format(**fields),
        t["leadin"].format(**fields),
        qs,
        focus_para,
        t["closing"].format(**fields),
        t["signoff"].format(**fields),
        _signature(cfg),
    )
    subject = t["subject"].format(**fields)
    note = "" if lang in LANG else "(No template for language '%s'; drafted in English.)" % lang
    return subject, body, note


def _queue_path(cfg):
    """The local inquiry queue lives at data/inquiries.json (sibling of data/jurisdictions/)."""
    return os.path.join(os.path.dirname(cfg.data_dir()), "inquiries.json")


def _load_existing(path):
    """Read the prior queue so human-set status/sent_at/reply survive a re-draft. Keyed by 'key'."""
    out = {}
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as fh:
                for q in json.load(fh):
                    if isinstance(q, dict) and q.get("key"):
                        out[q["key"]] = q
        except (OSError, ValueError):
            pass
    return out


def build_queue(cfg):
    """Scan data_dir(), draft for every open+contactable jurisdiction. Returns (drafts, open_no_contact)."""
    activities = list(cfg.activities)
    drafts, no_contact = [], []
    out_path = _queue_path(cfg)
    existing = _load_existing(out_path)

    for p in sorted(glob.glob(os.path.join(cfg.data_dir(), "*.json"))):
        try:
            with open(p, encoding="utf-8") as fh:
                d = json.load(fh)
        except (OSError, ValueError):
            continue
        if not isinstance(d, dict):
            continue
        jur = d.get("jurisdiction") or {}
        acts = d.get("activities") or {}
        open_acts = [k for k in activities if k in acts and is_open(acts[k])]
        # also surface any open non-configured activity present in the data
        open_acts += [k for k, v in acts.items() if k not in activities and is_open(v)]
        if not open_acts:
            continue

        contact, channel = pick_contact(d.get("contacts", []))
        name = jur.get("name") or jur.get("id") or os.path.splitext(os.path.basename(p))[0]
        if not contact:
            no_contact.append(name)
            continue

        lang = (d.get("inquiry_language") or jur.get("inquiry_language")
                or jur.get("language") or "en")
        agency = contact.get("agency", "") or "the relevant authority"
        subject, body, note = draft(cfg, d, lang, agency, open_acts, d.get("inquiry_focus", ""))
        jid = jur.get("id") or os.path.splitext(os.path.basename(p))[0]
        key = "%s::%s" % (jid, agency)
        prev = existing.get(key, {})
        drafts.append({
            "key": key,
            "jurisdiction_id": jid,
            "jurisdiction": name,
            "agency": agency,
            "language": lang,
            "channel": channel,
            "to": (contact.get("email") or "").strip(),
            "form_url": (contact.get("form_url") or "").strip(),
            "phone": (contact.get("phone") or "").strip(),
            "open_activities": open_acts,
            "subject": subject,
            "body": body,
            "note": note,
            # preserved human-set fields:
            "status": prev.get("status", "draft"),
            "sent_at": prev.get("sent_at", ""),
            "reply": prev.get("reply", ""),
        })

    return drafts, no_contact


def write_queue(cfg, drafts):
    path = _queue_path(cfg)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(drafts, fh, ensure_ascii=False, indent=2)
    return path


def main():
    cfg = config.load()
    if not cfg.inquiries_enabled:
        print("Inquiries module is OFF (config.inquiries.enabled = false).")
        print("This is the optional agency-inquiry module; enable it in config.json to draft inquiries.")
        return

    drafts, no_contact = build_queue(cfg)
    path = write_queue(cfg, drafts)

    print("Inquiries drafted: %d" % len(drafts))
    for q in drafts:
        tgt = "<%s>" % q["to"] if q["to"] else "(form: %s)" % q["form_url"]
        print("  [%-8s] %-8s %-2s %-16s -> %s %s" % (
            q["status"], q["channel"], q["language"], q["jurisdiction"][:16], q["agency"], tgt))
    print("Open but NO contact yet: %d%s" % (
        len(no_contact), (" (" + ", ".join(no_contact) + ")") if no_contact else ""))
    print("\nWrote %s" % path)


if __name__ == "__main__":
    main()
