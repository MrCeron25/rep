class Patent:
    def __init__(self, patent_name,
                 full_name_of_authors,
                 patent_type,
                 patent_number,
                 request_number,
                 registration_date,
                 patent_holders):
        # имя патента
        self.patent_name = patent_name
        # ФИО авторов
        self.full_name_of_authors = full_name_of_authors
        # тип патента
        self.patent_type = patent_type
        #  номер патента
        self.patent_number = patent_number
        # номер заявки
        self.request_number = request_number
        # дата регистрации
        self.registration_date = registration_date
        # патентообладатели
        self.patent_holders = patent_holders
