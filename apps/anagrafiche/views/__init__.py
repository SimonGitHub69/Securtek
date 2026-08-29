from .anagrafica import (
    AnagraficaListView,
    AnagraficaCreateView,
    AnagraficaUpdateView,
    AnagraficaDetailView,
    AnagraficaDeleteView,
)
from .contatto import (
    ContattoCreateView,
    ContattoUpdateView,
    ContattoDeleteView,
)
from .indirizzo import (
    IndirizzoCreateView,
    IndirizzoUpdateView,
    IndirizzoDeleteView,
)
from .personale import (
    PersonaleAnagraficaCreateView,
    PersonaleAnagraficaUpdateView,
    PersonaleAnagraficaDeleteView,
)
from .territorio import (
    ComuneCreateView,
    ComuneDeleteView,
    ComuneJsonView,
    ComuneListView,
    ComuneUpdateView,
    ProvinciaCreateView,
    ProvinciaDeleteView,
    ProvinciaListView,
    ProvinciaUpdateView,
)
