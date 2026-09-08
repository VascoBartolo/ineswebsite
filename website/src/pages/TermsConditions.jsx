import { Link } from 'react-router-dom';
import LegalLayout from './LegalLayout';
import { ENTITY, CANCELLATION_NOTICE_HOURS } from './legalInfo';

export default function TermsConditions() {
  return (
    <LegalLayout
      eyebrow="Informação legal"
      title="Termos e Condições"
      documentTitle="Termos e Condições"
    >
      <p className="legal-intro">
        Os presentes Termos e Condições regulam o acesso e a utilização do site{' '}
        {ENTITY.siteLabel} e de todos os serviços nele disponibilizados, incluindo o sistema de
        marcação e gestão de consultas de nutrição. São redigidos nos termos do Decreto-Lei
        n.º 7/2004, de 7 de janeiro (comércio eletrónico), do Decreto-Lei n.º 24/2014, de 14 de
        fevereiro (contratos celebrados à distância) e da Lei n.º 24/96, de 31 de julho (Lei de
        Defesa do Consumidor).
      </p>

      <section>
        <h2>1. Identificação do prestador de serviços</h2>
        <div className="legal-card">
          <dl>
            <dt>Prestador</dt>
            <dd>{ENTITY.name} ({ENTITY.brand}), {ENTITY.role}</dd>
            <dt>NIF</dt>
            <dd>{ENTITY.nif}</dd>
            <dt>Inscrição</dt>
            <dd>{ENTITY.professionalOrder} — {ENTITY.professionalId}</dd>
            <dt>Morada</dt>
            <dd>{ENTITY.address}</dd>
            <dt>E-mail</dt>
            <dd><a href={`mailto:${ENTITY.email}`}>{ENTITY.email}</a></dd>
            <dt>Telefone</dt>
            <dd><a href={`tel:${ENTITY.phoneHref}`}>{ENTITY.phone}</a></dd>
            <dt>Site</dt>
            <dd>{ENTITY.siteLabel}</dd>
          </dl>
        </div>
      </section>

      <section>
        <h2>2. Objeto e âmbito</h2>
        <p>
          Estes termos aplicam-se a toda a aplicação, designadamente: às páginas informativas do
          site, ao formulário de contacto, ao sistema de marcação de consultas, à consulta do
          estado de uma marcação, aos pedidos de alteração e cancelamento e às comunicações por
          e-mail associadas.
        </p>
      </section>

      <section>
        <h2>3. Aceitação</h2>
        <p>
          A utilização do site implica a aceitação integral e sem reservas destes Termos e
          Condições, bem como da{' '}
          <Link to="/politica-de-privacidade">Política de Privacidade</Link>. Quem não concorde
          com os mesmos deve abster-se de utilizar o site e os seus serviços.
        </p>
        <p>
          Ao submeter um pedido de marcação, o utilizador declara ter capacidade jurídica para o
          fazer e, tratando-se de consulta destinada a menor, ser titular das responsabilidades
          parentais ou estar por estes autorizado.
        </p>
      </section>

      <section>
        <h2>4. Natureza dos serviços</h2>
        <p>
          São prestados serviços de consulta de nutrição materno-infantil e pediátrica, em
          regime presencial ou online, por nutricionista inscrita na{' '}
          {ENTITY.professionalOrder} e sujeita ao respetivo Código Deontológico e a segredo
          profissional.
        </p>
        <div className="legal-notice">
          <p>
            O aconselhamento nutricional prestado <strong>não substitui a consulta, o diagnóstico
            ou o tratamento médico</strong>, nem constitui prescrição de medicamentos. Não deve
            interromper ou alterar qualquer tratamento médico com base na informação obtida
            através deste site.
          </p>
          <p>
            <strong>Em caso de emergência médica, contacte o 112 ou dirija-se ao serviço de
            urgência mais próximo.</strong> Este site não é um canal de atendimento urgente e as
            mensagens enviadas não são monitorizadas em permanência.
          </p>
        </div>
        <p>
          Os conteúdos informativos publicados no site têm natureza geral e não constituem
          aconselhamento individualizado. Os resultados de um plano nutricional dependem de
          fatores individuais, pelo que não são garantidos resultados específicos.
        </p>
      </section>

      <section>
        <h2>5. Marcação de consultas</h2>

        <h3>5.1. Processo de marcação</h3>
        <p>
          A submissão do formulário constitui um <strong>pedido de marcação</strong> e não uma
          consulta confirmada. O processo decorre da seguinte forma:
        </p>
        <ul>
          <li>
            o utilizador seleciona o tipo de consulta, o regime, a data e a hora entre os
            horários apresentados como disponíveis, e preenche os dados solicitados;
          </li>
          <li>
            submetido o pedido, é atribuída uma <strong>referência de marcação</strong> e enviado
            um e-mail de receção. A marcação fica no estado <em>pendente</em> e o horário fica
            reservado;
          </li>
          <li>
            a nutricionista aprecia o pedido e <strong>confirma</strong> ou solicita{' '}
            <strong>alteração</strong> do horário. Só com a confirmação a consulta se considera
            agendada, sendo enviado o respetivo e-mail;
          </li>
          <li>
            se for solicitada alteração, a marcação passa ao estado <em>necessita alteração</em>{' '}
            e o horário deixa de estar reservado.
          </li>
        </ul>
        <p>
          A disponibilidade apresentada é indicativa e depende da agenda em tempo real. Um
          horário pode deixar de estar disponível entre a seleção e a submissão do formulário,
          caso em que será pedido que escolha outro.
        </p>

        <h3>5.2. Dados fornecidos</h3>
        <p>
          O utilizador obriga-se a fornecer dados verdadeiros, exatos e atuais, em especial o
          endereço de e-mail e o contacto telefónico, uma vez que é através deles que toda a
          comunicação relativa à marcação é efetuada. Não é assumida responsabilidade por
          consultas não realizadas em virtude de dados de contacto incorretos ou desatualizados.
        </p>

        <h3>5.3. Consultas online</h3>
        <p>
          As consultas em regime online são realizadas por videochamada, cujo acesso é
          comunicado previamente por e-mail. É da responsabilidade do utilizador dispor de
          ligação à Internet, equipamento e condições de privacidade adequados. Falhas técnicas
          imputáveis ao utilizador não conferem direito a remarcação gratuita, sem prejuízo da
          avaliação de cada caso concreto.
        </p>
      </section>

      <section>
        <h2>6. Preços e pagamento</h2>
        <p>
          Os preços aplicáveis são os apresentados no momento da marcação, em euros e com todos
          os impostos incluídos, e variam consoante o regime (presencial ou online) e o facto de
          se tratar de primeira consulta ou de consulta de seguimento. O preço indicado no
          resumo da marcação é o preço devido.
        </p>
        <p>
          O site <strong>não processa pagamentos online</strong>. O pagamento é efetuado
          diretamente à nutricionista, nos termos acordados, sendo emitida fatura-recibo nos
          termos legais. Eventuais alterações de preços não afetam marcações já confirmadas.
        </p>
      </section>

      <section>
        <h2>7. Gestão da marcação pelo utilizador</h2>
        <p>
          Através da área <em>Gerir Marcação</em>, indicando a referência da marcação e o e-mail
          utilizado, o utilizador pode:
        </p>
        <ul>
          <li>consultar o estado atual da marcação;</li>
          <li>solicitar a alteração da data ou da hora, mediante mensagem à nutricionista;</li>
          <li>cancelar a consulta.</li>
        </ul>
        <p>
          O acesso a estas funcionalidades exige a referência e o e-mail associados à marcação,
          que funcionam como elementos de verificação. Compete ao utilizador mantê-los
          reservados. Não é possível cancelar através do site uma consulta cuja data e hora já
          tenham decorrido.
        </p>
      </section>

      <section>
        <h2>8. Cancelamento, remarcação e faltas</h2>
        <p>
          Os cancelamentos e pedidos de alteração devem ser efetuados com uma antecedência
          mínima de <strong>{CANCELLATION_NOTICE_HOURS} horas</strong> relativamente à hora
          marcada, através da área de gestão de marcação ou dos contactos indicados.
        </p>
        <p>
          A não comparência sem aviso prévio, ou o cancelamento efetuado com menos de{' '}
          {CANCELLATION_NOTICE_HOURS} horas de antecedência, poderá determinar a cobrança da
          consulta, salvo motivo de força maior devidamente justificado.
        </p>
        <p>
          A nutricionista reserva-se o direito de cancelar ou remarcar uma consulta por motivo
          justificado, designadamente doença ou impossibilidade superveniente, informando o
          utilizador com a maior brevidade possível e propondo nova data ou, não sendo esta
          aceite, devolvendo qualquer montante entretanto pago.
        </p>
      </section>

      <section>
        <h2>9. Direito de livre resolução</h2>
        <p>
          Tratando-se de contrato celebrado à distância com um consumidor, assiste ao utilizador
          o direito de <strong>livre resolução no prazo de 14 dias</strong> a contar da data de
          celebração do contrato, sem necessidade de indicar qualquer motivo e sem encargos, nos
          termos dos artigos 10.º e seguintes do Decreto-Lei n.º 24/2014, de 14 de fevereiro.
        </p>
        <p>
          Para exercer este direito basta comunicar essa decisão, de forma inequívoca, para{' '}
          <a href={`mailto:${ENTITY.email}`}>{ENTITY.email}</a>. O reembolso de qualquer montante
          pago é efetuado no prazo de 14 dias a contar da receção da comunicação.
        </p>
        <p>
          Nos termos do artigo 17.º, n.º 1, alínea a), do mesmo diploma, o direito de livre
          resolução <strong>não pode ser exercido depois de o serviço ter sido integralmente
          prestado</strong>, quando a execução tenha tido início com o acordo expresso do
          consumidor e com o reconhecimento de que perderia esse direito uma vez o serviço
          integralmente prestado. Se a consulta se realizar dentro do prazo de 14 dias a pedido
          do utilizador, este aceita que o direito de livre resolução se extingue com a
          realização da consulta.
        </p>
        <p>
          Este direito é autónomo e não prejudica a política de cancelamento prevista no
          ponto 8, que se aplica às consultas marcadas para data posterior ao termo do prazo de
          14 dias.
        </p>
      </section>

      <section>
        <h2>10. Obrigações e deveres do utilizador</h2>
        <p>O utilizador obriga-se a:</p>
        <ul>
          <li>utilizar o site de forma lícita e de acordo com estes termos;</li>
          <li>fornecer informação verdadeira e mantê-la atualizada;</li>
          <li>
            não submeter marcações falsas, em nome de terceiros sem autorização, ou em número
            manifestamente abusivo;
          </li>
          <li>
            não tentar aceder a áreas reservadas, contornar mecanismos de segurança ou de
            limitação de pedidos, nem interferir com o normal funcionamento do serviço;
          </li>
          <li>
            não introduzir nos campos de texto livre conteúdos ilícitos, ofensivos ou dados
            pessoais de terceiros sem legitimidade para o fazer.
          </li>
        </ul>
        <p>
          O incumprimento destes deveres confere o direito de recusar ou anular marcações e de
          restringir o acesso ao serviço, sem prejuízo da responsabilidade civil e criminal a
          que haja lugar.
        </p>
      </section>

      <section>
        <h2>11. Propriedade intelectual</h2>
        <p>
          Todos os conteúdos do site — textos, imagens, fotografias, logótipo, identidade
          visual, código e estrutura — são propriedade de {ENTITY.name} ou de terceiros que
          autorizaram a sua utilização, e encontram-se protegidos pelo Código do Direito de
          Autor e dos Direitos Conexos.
        </p>
        <p>
          É proibida a reprodução, distribuição, transformação ou comunicação pública, total ou
          parcial, sem autorização prévia e escrita, salvo para uso pessoal e não comercial. Os
          planos alimentares e demais materiais entregues em consulta destinam-se a uso
          exclusivamente pessoal do utente, não podendo ser partilhados ou comercializados.
        </p>
      </section>

      <section>
        <h2>12. Disponibilidade do serviço e responsabilidade</h2>
        <p>
          São envidados os melhores esforços para manter o site disponível e a informação
          correta e atualizada. Não é, contudo, garantida a disponibilidade ininterrupta,
          podendo o serviço ser suspenso por manutenção, falha técnica, avaria de fornecedores
          ou motivo de força maior.
        </p>
        <p>
          Na medida do permitido por lei, não é assumida responsabilidade por danos resultantes
          da indisponibilidade temporária do site, de falhas na entrega de mensagens de correio
          eletrónico imputáveis a terceiros ou ao filtro de spam do destinatário, nem da
          utilização indevida da referência de marcação por terceiros a quem o utilizador a
          tenha divulgado. Nada nestes termos exclui a responsabilidade por dolo, culpa grave ou
          danos à saúde, nem afeta os direitos que a lei confere ao consumidor.
        </p>
      </section>

      <section>
        <h2>13. Proteção de dados e segredo profissional</h2>
        <p>
          O tratamento de dados pessoais é descrito em detalhe na{' '}
          <Link to="/politica-de-privacidade">Política de Privacidade</Link>, que faz parte
          integrante destes termos. Toda a informação clínica está abrangida pelo segredo
          profissional a que a nutricionista está vinculada.
        </p>
      </section>

      <section>
        <h2>14. Reclamações e resolução de litígios</h2>
        <p>
          Qualquer reclamação pode ser apresentada diretamente para{' '}
          <a href={`mailto:${ENTITY.email}`}>{ENTITY.email}</a> ou através do{' '}
          <a href="https://www.livroreclamacoes.pt/inicio" target="_blank" rel="noopener noreferrer">
            Livro de Reclamações Eletrónico
          </a>.
        </p>
        <p>
          Em caso de litígio de consumo, o consumidor pode recorrer a uma entidade de resolução
          alternativa de litígios, nos termos da Lei n.º 144/2015, de 8 de setembro. A lista
          atualizada das entidades competentes, incluindo a territorialmente competente na
          Região Autónoma dos Açores, está disponível no{' '}
          <a href="https://www.consumidor.gov.pt" target="_blank" rel="noopener noreferrer">
            Portal do Consumidor
          </a>.
        </p>
        <p>
          Podem ainda ser apresentadas participações relativas à conduta profissional junto da{' '}
          {ENTITY.professionalOrder}.
        </p>
      </section>

      <section>
        <h2>15. Alterações aos termos</h2>
        <p>
          Estes Termos e Condições podem ser alterados a qualquer momento, produzindo a nova
          versão efeitos a partir da sua publicação nesta página. Às marcações já confirmadas
          aplica-se a versão em vigor à data da respetiva confirmação.
        </p>
      </section>

      <section>
        <h2>16. Lei aplicável e foro</h2>
        <p>
          Aos presentes termos aplica-se a lei portuguesa. Para a resolução de qualquer litígio
          emergente da sua interpretação ou execução é competente o foro da comarca dos Açores,
          com expressa renúncia a qualquer outro, sem prejuízo das regras imperativas de
          competência aplicáveis aos consumidores.
        </p>
        <p>
          Se alguma cláusula for considerada inválida ou ineficaz, as restantes mantêm-se em
          vigor, sendo a cláusula afetada substituída por outra que, sendo válida, melhor
          corresponda ao fim pretendido.
        </p>
      </section>
    </LegalLayout>
  );
}
