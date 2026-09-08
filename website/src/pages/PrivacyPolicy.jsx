import LegalLayout from './LegalLayout';
import { ENTITY } from './legalInfo';

export default function PrivacyPolicy() {
  return (
    <LegalLayout
      eyebrow="Informação legal"
      title="Política de Privacidade"
      documentTitle="Política de Privacidade"
    >
      <p className="legal-intro">
        Esta Política de Privacidade explica que dados pessoais são recolhidos através do site{' '}
        {ENTITY.siteLabel}, incluindo o sistema de marcação e gestão de consultas, com que
        finalidades são tratados, durante quanto tempo são conservados e que direitos lhe
        assistem. Foi elaborada nos termos do Regulamento (UE) 2016/679 (RGPD) e da Lei
        n.º 58/2019, de 8 de agosto.
      </p>

      <section>
        <h2>1. Responsável pelo tratamento</h2>
        <div className="legal-card">
          <dl>
            <dt>Responsável</dt>
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
          </dl>
        </div>
        <p>
          Não está designado um Encarregado de Proteção de Dados, por não se verificarem os
          requisitos do artigo 37.º do RGPD. Qualquer questão relativa a dados pessoais deve
          ser dirigida aos contactos acima.
        </p>
      </section>

      <section>
        <h2>2. Âmbito de aplicação</h2>
        <p>Esta política aplica-se a todo o serviço, nomeadamente:</p>
        <ul>
          <li>ao site institucional e às suas páginas informativas;</li>
          <li>ao formulário de contacto;</li>
          <li>
            ao sistema de <strong>marcação e gestão de consultas</strong> (pedido de marcação,
            consulta do estado da marcação, pedido de alteração e cancelamento);
          </li>
          <li>à comunicação por e-mail associada às marcações;</li>
          <li>à área reservada de administração utilizada pela nutricionista.</li>
        </ul>
        <p>
          Não se aplica a sites de terceiros acessíveis a partir de ligações aqui
          disponibilizadas, que têm as suas próprias políticas de privacidade.
        </p>
      </section>

      <section>
        <h2>3. Dados pessoais recolhidos</h2>

        <h3>3.1. Marcação de consulta</h3>
        <p>
          Para submeter um pedido de marcação são recolhidos: tipo de destinatário da consulta
          (adulto ou bebé/criança), tipo de consulta, regime (presencial ou online), local da
          consulta quando presencial, nome, idade, endereço de e-mail, contacto telefónico,
          data e hora pretendidas e, facultativamente, um campo de contexto livre onde pode
          descrever o motivo da consulta. É ainda gerada uma referência interna da marcação e
          registado o respetivo estado.
        </p>

        <h3>3.2. Dados relativos à saúde</h3>
        <div className="legal-notice">
          <p>
            O campo de contexto e a informação partilhada no âmbito da consulta podem conter{' '}
            <strong>dados relativos à saúde</strong>, que constituem uma categoria especial de
            dados pessoais (artigo 9.º do RGPD). Estes dados são tratados exclusivamente para a
            prestação de cuidados de nutrição, ao abrigo do artigo 9.º, n.º 2, alínea h), do
            RGPD, por profissional sujeita a <strong>segredo profissional</strong> nos termos do
            Código Deontológico da {ENTITY.professionalOrder}.
          </p>
          <p>
            Pedimos que <strong>não inclua no formulário mais informação clínica do que a
            necessária</strong> para enquadrar o pedido de marcação. O historial clínico
            detalhado é recolhido em consulta.
          </p>
        </div>

        <h3>3.3. Dados de menores</h3>
        <p>
          Nas consultas de nutrição materno-infantil e pediátrica são tratados dados de bebés e
          crianças. Esses dados são fornecidos pelos <strong>titulares das responsabilidades
          parentais</strong>, que declaram, ao submeter o formulário, estar legitimados para o
          fazer. O site não se destina a ser utilizado diretamente por menores.
        </p>

        <h3>3.4. Formulário de contacto</h3>
        <p>
          Nome, endereço de e-mail, contacto telefónico (facultativo), assunto e mensagem. Estes
          dados são enviados por e-mail para a caixa de correio da nutricionista e não são
          guardados na base de dados do site.
        </p>

        <h3>3.5. Dados técnicos</h3>
        <p>
          Por razões de segurança e de funcionamento, o servidor regista o método e o endereço
          do pedido, o código de resposta e o endereço IP de origem. Estes registos são usados
          para deteção de abusos e limitação do número de pedidos por origem, e não são
          utilizados para criar perfis nem para publicidade.
        </p>

        <h3>3.6. Área de administração</h3>
        <p>
          O acesso à área reservada gera um token de sessão autenticado, guardado num cookie
          técnico. Aplica-se apenas à nutricionista, não a visitantes do site (ver o ponto 9).
        </p>
      </section>

      <section>
        <h2>4. Finalidades e fundamentos de licitude</h2>
        <div className="legal-table-wrap">
          <table className="legal-table">
            <thead>
              <tr>
                <th>Finalidade</th>
                <th>Dados</th>
                <th>Fundamento de licitude</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Registar, confirmar e gerir pedidos de marcação de consulta</td>
                <td>Identificação e contacto, dados da marcação</td>
                <td>Artigo 6.º, n.º 1, al. b) — diligências pré-contratuais e execução do contrato</td>
              </tr>
              <tr>
                <td>Prestação de cuidados de nutrição</td>
                <td>Dados relativos à saúde</td>
                <td>Artigo 9.º, n.º 2, al. h) — prestação de cuidados de saúde por profissional sujeita a segredo</td>
              </tr>
              <tr>
                <td>Envio de e-mails transacionais (marcação recebida, confirmação, alteração, cancelamento)</td>
                <td>Nome, e-mail, dados da marcação</td>
                <td>Artigo 6.º, n.º 1, al. b) — execução do contrato</td>
              </tr>
              <tr>
                <td>Gestão da agenda e prevenção de sobreposição de consultas</td>
                <td>Data, hora, duração, regime e local</td>
                <td>Artigo 6.º, n.º 1, al. b) — execução do contrato</td>
              </tr>
              <tr>
                <td>Resposta a mensagens enviadas pelo formulário de contacto</td>
                <td>Nome, e-mail, telefone, mensagem</td>
                <td>Artigo 6.º, n.º 1, al. f) — interesse legítimo em responder a quem nos contacta</td>
              </tr>
              <tr>
                <td>Faturação e cumprimento de obrigações fiscais e contabilísticas</td>
                <td>Identificação, dados de faturação, valor</td>
                <td>Artigo 6.º, n.º 1, al. c) — cumprimento de obrigação jurídica</td>
              </tr>
              <tr>
                <td>Segurança do serviço, prevenção de abuso e registo de acessos</td>
                <td>Endereço IP e registos de pedidos</td>
                <td>Artigo 6.º, n.º 1, al. f) — interesse legítimo na segurança do sistema</td>
              </tr>
              <tr>
                <td>Autenticação na área de administração</td>
                <td>Cookie técnico de sessão</td>
                <td>Artigo 6.º, n.º 1, al. f) — interesse legítimo em proteger o acesso</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p>
          Não é realizada qualquer decisão exclusivamente automatizada com efeitos jurídicos,
          nem definição de perfis, nem envio de comunicações de marketing sem consentimento
          prévio e autónomo.
        </p>
      </section>

      <section>
        <h2>5. Prazos de conservação</h2>
        <div className="legal-table-wrap">
          <table className="legal-table">
            <thead>
              <tr>
                <th>Categoria</th>
                <th>Prazo</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Registo clínico e dados de saúde de utentes</td>
                <td>Pelo prazo legalmente exigido para a conservação de registos clínicos e, no mínimo, 5 anos após o último contacto</td>
              </tr>
              <tr>
                <td>Dados de marcações e histórico de consultas</td>
                <td>Enquanto durar a relação com o utente e, após o seu termo, pelo prazo de prescrição aplicável</td>
              </tr>
              <tr>
                <td>Documentos de faturação e suporte contabilístico</td>
                <td>10 anos, nos termos da legislação fiscal aplicável</td>
              </tr>
              <tr>
                <td>Marcações canceladas ou não confirmadas</td>
                <td>Até 12 meses, salvo se necessárias para prova ou defesa de direitos</td>
              </tr>
              <tr>
                <td>Mensagens do formulário de contacto</td>
                <td>Até 12 meses após a resposta, salvo se derem origem a marcação</td>
              </tr>
              <tr>
                <td>Registos técnicos de acesso</td>
                <td>Até 12 meses</td>
              </tr>
              <tr>
                <td>Cookie de sessão de administração</td>
                <td>Expira automaticamente; é eliminado ao terminar sessão</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p>
          Findos os prazos, os dados são eliminados ou anonimizados de forma irreversível.
        </p>
      </section>

      <section>
        <h2>6. Destinatários e subcontratantes</h2>
        <p>
          Os dados não são vendidos nem cedidos a terceiros para fins comerciais. São, no
          entanto, tratados por prestadores de serviços que atuam como subcontratantes, ao
          abrigo de contratos de tratamento de dados nos termos do artigo 28.º do RGPD:
        </p>
        <ul>
          <li>
            <strong>Fornecedor de alojamento e base de dados</strong> — alojamento da aplicação e
            armazenamento dos dados de marcação.
          </li>
          <li>
            <strong>Fornecedor de correio eletrónico</strong> — envio dos e-mails transacionais
            de marcação, confirmação, alteração e cancelamento, e receção das mensagens do
            formulário de contacto.
          </li>
          <li>
            <strong>Google (Google Calendar)</strong> — a agenda profissional é gerida no Google
            Calendar. Quando uma marcação é confirmada, é criado um evento com os dados
            necessários à realização da consulta.
          </li>
          <li>
            <strong>Google (Google Fonts)</strong> — as tipografias do site são carregadas a
            partir dos servidores da Google, o que implica a transmissão do seu endereço IP à
            Google no momento em que a página é aberta.
          </li>
        </ul>
        <p>
          Os dados podem ainda ser comunicados a autoridades públicas quando exista obrigação
          legal de o fazer, bem como a contabilista certificado no âmbito das obrigações
          fiscais.
        </p>
      </section>

      <section>
        <h2>7. Transferências internacionais</h2>
        <p>
          O tratamento ocorre, em regra, dentro do Espaço Económico Europeu. Quando algum
          subcontratante implique o acesso a dados a partir de países terceiros, tal ocorre ao
          abrigo de uma decisão de adequação da Comissão Europeia ou de Cláusulas Contratuais
          Tipo aprovadas nos termos do artigo 46.º do RGPD, acompanhadas de medidas
          complementares de segurança.
        </p>
      </section>

      <section>
        <h2>8. Segurança</h2>
        <p>
          São aplicadas medidas técnicas e organizativas adequadas ao risco, designadamente:
          comunicação cifrada por HTTPS; autenticação da área reservada com palavra-passe
          guardada sob a forma de resumo criptográfico e sessão em cookie <em>HttpOnly</em>,{' '}
          <em>Secure</em> e <em>SameSite=Strict</em>; limitação do número de pedidos por origem;
          validação e limitação do tamanho dos dados submetidos; ligações de gestão de marcação
          assinadas criptograficamente e com validade limitada; e acesso aos dados restrito à
          nutricionista, sujeita a segredo profissional.
        </p>
        <p>
          Em caso de violação de dados pessoais suscetível de resultar num risco para os seus
          direitos e liberdades, a Comissão Nacional de Proteção de Dados será notificada nos
          termos do artigo 33.º do RGPD e, quando o risco for elevado, será também informado o
          titular dos dados.
        </p>
      </section>

      <section>
        <h2>9. Cookies e tecnologias semelhantes</h2>
        <p>
          Este site <strong>não utiliza cookies de análise, de publicidade, de redes sociais ou
          de perfilagem</strong>, nem qualquer ferramenta de estatísticas de visitantes. Não são
          utilizados <em>pixels</em> de seguimento nem armazenamento local do navegador para
          acompanhar a sua navegação.
        </p>
        <p>É utilizado um único cookie, estritamente necessário:</p>
        <div className="legal-table-wrap">
          <table className="legal-table">
            <thead>
              <tr>
                <th>Cookie</th>
                <th>Finalidade</th>
                <th>Duração</th>
                <th>Tipo</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><code>admin_token</code></td>
                <td>Manter a sessão autenticada na área reservada de administração da agenda</td>
                <td>Sessão, com expiração automática</td>
                <td>Estritamente necessário (primeira parte)</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p>
          Este cookie é criado apenas quando a nutricionista inicia sessão na área reservada, e
          está limitado a esse caminho. <strong>Nunca é criado durante a navegação normal no
          site nem durante a marcação de uma consulta.</strong>
        </p>
        <p>
          Por se tratar de um cookie estritamente necessário à prestação de um serviço
          expressamente solicitado pelo utilizador, está dispensado de consentimento prévio, nos
          termos do artigo 5.º, n.º 3, da Lei n.º 41/2004, de 18 de agosto. É por esse motivo
          que o site não apresenta qualquer banner de cookies. Caso venham a ser introduzidas
          tecnologias não essenciais, será previamente pedido o seu consentimento e esta
          política será atualizada.
        </p>
      </section>

      <section>
        <h2>10. Os seus direitos</h2>
        <p>Enquanto titular dos dados, assistem-lhe os seguintes direitos:</p>
        <ul>
          <li><strong>Acesso</strong> — saber que dados seus são tratados e obter uma cópia;</li>
          <li><strong>Retificação</strong> — corrigir dados inexatos ou incompletos;</li>
          <li>
            <strong>Apagamento</strong> — solicitar a eliminação dos dados, quando não subsista
            obrigação legal de conservação;
          </li>
          <li><strong>Limitação</strong> — restringir o tratamento em determinadas situações;</li>
          <li>
            <strong>Portabilidade</strong> — receber os dados em formato estruturado e de uso
            corrente;
          </li>
          <li>
            <strong>Oposição</strong> — opor-se a tratamentos fundados em interesse legítimo;
          </li>
          <li>
            <strong>Retirada do consentimento</strong> — sempre que o tratamento se baseie em
            consentimento, sem afetar a licitude do tratamento anterior.
          </li>
        </ul>
        <p>
          Os pedidos devem ser dirigidos a <a href={`mailto:${ENTITY.email}`}>{ENTITY.email}</a>{' '}
          e serão respondidos no prazo de um mês, prorrogável nos termos do artigo 12.º, n.º 3,
          do RGPD. Pode ser solicitada informação adicional para confirmar a sua identidade,
          nomeadamente quando o pedido envolva dados de saúde.
        </p>
        <p>
          Tem também o direito de apresentar reclamação à autoridade de controlo:{' '}
          <strong>Comissão Nacional de Proteção de Dados (CNPD)</strong>, Av. D. Carlos I,
          n.º 134, 1.º, 1200-651 Lisboa —{' '}
          <a href="https://www.cnpd.pt" target="_blank" rel="noopener noreferrer">www.cnpd.pt</a>.
        </p>
      </section>

      <section>
        <h2>11. Carácter obrigatório da recolha</h2>
        <p>
          Os campos assinalados como obrigatórios no formulário de marcação são indispensáveis
          para o registo e a gestão da consulta. A sua não disponibilização impossibilita a
          marcação. Os campos facultativos, como o contexto clínico, destinam-se apenas a
          preparar melhor a consulta.
        </p>
      </section>

      <section>
        <h2>12. Ligações para sites de terceiros</h2>
        <p>
          O site contém ligações para o Instagram e para o WhatsApp. Ao segui-las, passa a estar
          sujeito às políticas de privacidade dessas plataformas, pelas quais não é assumida
          qualquer responsabilidade.
        </p>
      </section>

      <section>
        <h2>13. Alterações a esta política</h2>
        <p>
          Esta política pode ser atualizada sempre que se justifique, designadamente por
          alteração dos serviços prestados ou da legislação aplicável. A versão em vigor é a
          publicada nesta página, com indicação da data da última atualização.
        </p>
      </section>
    </LegalLayout>
  );
}
