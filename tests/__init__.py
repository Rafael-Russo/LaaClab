def load_tests(loader, tests, pattern):
    """Suíte Flask — coletada pelo pytest, nunca pelo runner do Django.

    O ``DiscoverRunner`` varre a raiz do repositório e importaria todo
    ``test_*.py`` daqui. Devolver uma suíte vazia impede que um erro de import
    num teste Flask quebre o passo do Django com a atribuição errada.
    """
    return loader.suiteClass()
