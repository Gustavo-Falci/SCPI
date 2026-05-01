--
-- PostgreSQL database dump
--

\restrict cDx2cdXHh6hBoN2KIPfnkBPgCVtBxezcaiUGRCdtCOkR4vonSsDZvuOee5Gwirm

-- Dumped from database version 16.13 (Ubuntu 16.13-0ubuntu0.24.04.1)
-- Dumped by pg_dump version 18.1

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alunos; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alunos (
    aluno_id uuid NOT NULL,
    usuario_id uuid NOT NULL,
    ra character varying(100) NOT NULL,
    turno character varying(20),
    CONSTRAINT alunos_turno_check CHECK (((turno)::text = ANY ((ARRAY['Matutino'::character varying, 'Noturno'::character varying])::text[])))
);


--
-- Name: chamadas; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.chamadas (
    chamada_id integer NOT NULL,
    turma_id uuid NOT NULL,
    professor_id uuid NOT NULL,
    data_chamada date NOT NULL,
    horario_inicio time without time zone NOT NULL,
    horario_fim time without time zone,
    status character varying(50) DEFAULT 'Aberta'::character varying,
    data_criacao timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: chamadas_chamada_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.chamadas_chamada_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: chamadas_chamada_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.chamadas_chamada_id_seq OWNED BY public.chamadas.chamada_id;


--
-- Name: colecao_rostos; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.colecao_rostos (
    colecao_rosto_id integer NOT NULL,
    aluno_id uuid NOT NULL,
    external_image_id character varying(255) NOT NULL,
    face_id_rekognition character varying(255),
    s3_path_cadastro character varying(500),
    data_indexacao timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    consentimento_biometrico boolean DEFAULT false NOT NULL,
    consentimento_data timestamp without time zone,
    revogado_em timestamp without time zone
);


--
-- Name: colecao_rostos_colecao_rosto_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.colecao_rostos_colecao_rosto_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: colecao_rostos_colecao_rosto_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.colecao_rostos_colecao_rosto_id_seq OWNED BY public.colecao_rostos.colecao_rosto_id;


--
-- Name: horarios_aulas; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.horarios_aulas (
    horario_id uuid DEFAULT gen_random_uuid() NOT NULL,
    turma_id uuid,
    dia_semana integer,
    horario_inicio time without time zone,
    horario_fim time without time zone,
    sala text
);


--
-- Name: passwordresetcodes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.passwordresetcodes (
    id integer NOT NULL,
    email character varying(255) NOT NULL,
    code character varying(6) NOT NULL,
    expires_at timestamp without time zone NOT NULL,
    used boolean DEFAULT false NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL
);


--
-- Name: passwordresetcodes_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.passwordresetcodes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: passwordresetcodes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.passwordresetcodes_id_seq OWNED BY public.passwordresetcodes.id;


--
-- Name: presencas; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.presencas (
    presenca_id integer NOT NULL,
    chamada_id integer NOT NULL,
    aluno_id uuid NOT NULL,
    hora_registro timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    tipo_registro character varying(50) DEFAULT 'Reconhecimento'::character varying
);


--
-- Name: presencas_presenca_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.presencas_presenca_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: presencas_presenca_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.presencas_presenca_id_seq OWNED BY public.presencas.presenca_id;


--
-- Name: professores; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.professores (
    professor_id uuid NOT NULL,
    usuario_id uuid NOT NULL,
    departamento character varying(150),
    data_admissao date
);


--
-- Name: pushtokens; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pushtokens (
    usuario_id character varying(64) NOT NULL,
    expo_token text NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: refreshtokens; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.refreshtokens (
    token_hash character varying(128) NOT NULL,
    usuario_id character varying(64) NOT NULL,
    expires_at timestamp without time zone NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    revoked_at timestamp without time zone
);


--
-- Name: turma_alunos; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.turma_alunos (
    turma_aluno_id integer NOT NULL,
    turma_id uuid NOT NULL,
    aluno_id uuid NOT NULL,
    data_associacao timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: turma_alunos_turma_aluno_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.turma_alunos_turma_aluno_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: turma_alunos_turma_aluno_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.turma_alunos_turma_aluno_id_seq OWNED BY public.turma_alunos.turma_aluno_id;


--
-- Name: turmas; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.turmas (
    turma_id uuid NOT NULL,
    professor_id uuid,
    codigo_turma character varying(50) NOT NULL,
    nome_disciplina character varying(255) NOT NULL,
    periodo_letivo character varying(50),
    sala_padrao character varying(100),
    turno character varying(20),
    semestre character varying(20)
);


--
-- Name: usuarios; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.usuarios (
    usuario_id uuid NOT NULL,
    nome character varying(255) NOT NULL,
    email character varying(255) NOT NULL,
    senha character varying(255) NOT NULL,
    tipo_usuario character varying(50) NOT NULL,
    data_cadastro timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    primeiro_acesso boolean DEFAULT false NOT NULL
);


--
-- Name: chamadas chamada_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chamadas ALTER COLUMN chamada_id SET DEFAULT nextval('public.chamadas_chamada_id_seq'::regclass);


--
-- Name: colecao_rostos colecao_rosto_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.colecao_rostos ALTER COLUMN colecao_rosto_id SET DEFAULT nextval('public.colecao_rostos_colecao_rosto_id_seq'::regclass);


--
-- Name: passwordresetcodes id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.passwordresetcodes ALTER COLUMN id SET DEFAULT nextval('public.passwordresetcodes_id_seq'::regclass);


--
-- Name: presencas presenca_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.presencas ALTER COLUMN presenca_id SET DEFAULT nextval('public.presencas_presenca_id_seq'::regclass);


--
-- Name: turma_alunos turma_aluno_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.turma_alunos ALTER COLUMN turma_aluno_id SET DEFAULT nextval('public.turma_alunos_turma_aluno_id_seq'::regclass);


--
-- Name: alunos alunos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alunos
    ADD CONSTRAINT alunos_pkey PRIMARY KEY (aluno_id);


--
-- Name: alunos alunos_ra_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alunos
    ADD CONSTRAINT alunos_ra_key UNIQUE (ra);


--
-- Name: alunos alunos_usuario_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alunos
    ADD CONSTRAINT alunos_usuario_id_key UNIQUE (usuario_id);


--
-- Name: chamadas chamadas_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chamadas
    ADD CONSTRAINT chamadas_pkey PRIMARY KEY (chamada_id);


--
-- Name: colecao_rostos colecao_rostos_external_image_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.colecao_rostos
    ADD CONSTRAINT colecao_rostos_external_image_id_key UNIQUE (external_image_id);


--
-- Name: colecao_rostos colecao_rostos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.colecao_rostos
    ADD CONSTRAINT colecao_rostos_pkey PRIMARY KEY (colecao_rosto_id);


--
-- Name: horarios_aulas horarios_aulas_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.horarios_aulas
    ADD CONSTRAINT horarios_aulas_pkey PRIMARY KEY (horario_id);


--
-- Name: passwordresetcodes passwordresetcodes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.passwordresetcodes
    ADD CONSTRAINT passwordresetcodes_pkey PRIMARY KEY (id);


--
-- Name: presencas presencas_chamada_id_aluno_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.presencas
    ADD CONSTRAINT presencas_chamada_id_aluno_id_key UNIQUE (chamada_id, aluno_id);


--
-- Name: presencas presencas_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.presencas
    ADD CONSTRAINT presencas_pkey PRIMARY KEY (presenca_id);


--
-- Name: professores professores_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.professores
    ADD CONSTRAINT professores_pkey PRIMARY KEY (professor_id);


--
-- Name: professores professores_usuario_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.professores
    ADD CONSTRAINT professores_usuario_id_key UNIQUE (usuario_id);


--
-- Name: pushtokens pushtokens_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pushtokens
    ADD CONSTRAINT pushtokens_pkey PRIMARY KEY (usuario_id);


--
-- Name: refreshtokens refreshtokens_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.refreshtokens
    ADD CONSTRAINT refreshtokens_pkey PRIMARY KEY (token_hash);


--
-- Name: turma_alunos turma_alunos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.turma_alunos
    ADD CONSTRAINT turma_alunos_pkey PRIMARY KEY (turma_aluno_id);


--
-- Name: turma_alunos turma_alunos_turma_id_aluno_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.turma_alunos
    ADD CONSTRAINT turma_alunos_turma_id_aluno_id_key UNIQUE (turma_id, aluno_id);


--
-- Name: turmas turmas_codigo_turma_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.turmas
    ADD CONSTRAINT turmas_codigo_turma_key UNIQUE (codigo_turma);


--
-- Name: turmas turmas_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.turmas
    ADD CONSTRAINT turmas_pkey PRIMARY KEY (turma_id);


--
-- Name: usuarios usuarios_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuarios
    ADD CONSTRAINT usuarios_email_key UNIQUE (email);


--
-- Name: usuarios usuarios_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuarios
    ADD CONSTRAINT usuarios_pkey PRIMARY KEY (usuario_id);


--
-- Name: idx_refresh_usuario; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_refresh_usuario ON public.refreshtokens USING btree (usuario_id);


--
-- Name: alunos alunos_usuario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alunos
    ADD CONSTRAINT alunos_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuarios(usuario_id) ON DELETE CASCADE;


--
-- Name: chamadas chamadas_professor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chamadas
    ADD CONSTRAINT chamadas_professor_id_fkey FOREIGN KEY (professor_id) REFERENCES public.professores(professor_id) ON DELETE CASCADE;


--
-- Name: chamadas chamadas_turma_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chamadas
    ADD CONSTRAINT chamadas_turma_id_fkey FOREIGN KEY (turma_id) REFERENCES public.turmas(turma_id) ON DELETE CASCADE;


--
-- Name: colecao_rostos colecao_rostos_aluno_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.colecao_rostos
    ADD CONSTRAINT colecao_rostos_aluno_id_fkey FOREIGN KEY (aluno_id) REFERENCES public.alunos(aluno_id) ON DELETE CASCADE;


--
-- Name: horarios_aulas horarios_aulas_turma_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.horarios_aulas
    ADD CONSTRAINT horarios_aulas_turma_id_fkey FOREIGN KEY (turma_id) REFERENCES public.turmas(turma_id);


--
-- Name: presencas presencas_aluno_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.presencas
    ADD CONSTRAINT presencas_aluno_id_fkey FOREIGN KEY (aluno_id) REFERENCES public.alunos(aluno_id) ON DELETE CASCADE;


--
-- Name: presencas presencas_chamada_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.presencas
    ADD CONSTRAINT presencas_chamada_id_fkey FOREIGN KEY (chamada_id) REFERENCES public.chamadas(chamada_id) ON DELETE CASCADE;


--
-- Name: professores professores_usuario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.professores
    ADD CONSTRAINT professores_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuarios(usuario_id) ON DELETE CASCADE;


--
-- Name: turma_alunos turma_alunos_aluno_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.turma_alunos
    ADD CONSTRAINT turma_alunos_aluno_id_fkey FOREIGN KEY (aluno_id) REFERENCES public.alunos(aluno_id) ON DELETE CASCADE;


--
-- Name: turma_alunos turma_alunos_turma_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.turma_alunos
    ADD CONSTRAINT turma_alunos_turma_id_fkey FOREIGN KEY (turma_id) REFERENCES public.turmas(turma_id) ON DELETE CASCADE;


--
-- Name: turmas turmas_professor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.turmas
    ADD CONSTRAINT turmas_professor_id_fkey FOREIGN KEY (professor_id) REFERENCES public.professores(professor_id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict cDx2cdXHh6hBoN2KIPfnkBPgCVtBxezcaiUGRCdtCOkR4vonSsDZvuOee5Gwirm

