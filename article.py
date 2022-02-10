class Article:
    def __init__(self, article_title, full_name_of_authors, isbn=None):
        # название статьи
        self.article_title = article_title
        # ФИО авторов
        self.full_name_of_authors = full_name_of_authors
        # Международный стандартный номер книги или ISBN (International Standard Book Number)
        self.isbn = isbn

    def to_list(self):
        return [self.article_title, self.full_name_of_authors, self.isbn]

    def __str__(self):
        return f'article_title=\'{self.article_title}\'\n' \
               f'full_name_of_authors={self.full_name_of_authors}\n' \
               f'isbn={self.isbn}'
