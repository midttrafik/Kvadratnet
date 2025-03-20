from abc import ABC, abstractmethod

class DataLoader(ABC):
    """ Strategy Interface til indlæsning af data.
    """
    
    @abstractmethod
    def get_data(self):
        """ Indlæs data, lav punkt geometri, udfør filtrering hvis nødvendigt og opsæt i standardformat.
        """
        pass