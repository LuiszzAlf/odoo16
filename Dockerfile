FROM odoo:16.0
USER root
COPY . .
RUN echo "Instalando dependencias pip"
# RUN apt install python-pip -y
RUN apt update
RUN pip install -r requirements.txt
RUN echo "Instalando dependencias barcode"
# RUN pip install pybarcode --pre
RUN echo "Finish :)"
# CMD odoo --dev=xml