/*
Удаление настроек старых пользователей
Запуск скрипта:
psql postgresql://db_user:db_password@db_host/db_name -v ON_ERROR_STOP=ON -f /r/bustime/bustime/utils/clean_usersettings.sql
Читать:
https://dwgeek.com/redshift-set-on_error_stop-using-psql-examples.html/
*/

-- сначала выберем все ID настроек старых пользователей
WITH ids AS (
	-- этот запрос вычисляется только один раз для любого количества внешних запросов
	SELECT id
	FROM bustime_usersettings
	WHERE user_id is NULL               -- пользователья нет в таблице Users (не зарегистрирован на сайте)
	AND CURRENT_DATE - DATE(mtime) > 90 -- и он не заходил на сайт более 90 дней
	-- закомментировать после отладки
	--LIMIT 1
)
-- а это "внешние" запросы
-- шерстим все зависимости от удаляемых настроек
-- порядок обработки не важен и здесь соответствует поределениям моделей в models.py для удобства

-- Favorites, on_delete=models.CASCADE
,Favorites     AS (DELETE FROM bustime_favorites                 WHERE us_id   IN (select id from ids))

-- Log, on_delete=models.SET_NULL
,Log           AS (UPDATE bustime_log         SET user_id = NULL WHERE user_id IN (select id from ids))

-- Gosnum, on_delete=models.SET_NULL
,Gosnum        AS (UPDATE bustime_gosnum      SET us_id   = NULL WHERE us_id   IN (select id from ids))

-- Transaction, on_delete=models.SET_NULL
,"Transaction" AS (UPDATE bustime_transaction SET user_id = NULL WHERE user_id IN (select id from ids))

-- SpecialIcon, on_delete=models.SET_NULL
,SpecialIcon   AS (UPDATE bustime_specialicon SET us_id   = NULL WHERE us_id   IN (select id from ids))

-- Vote, on_delete=models.SET_NULL
,Vote          AS (UPDATE bustime_vote        SET us_id   = NULL WHERE us_id   IN (select id from ids))

-- GVote, on_delete=models.CASCADE
,GVote         AS (DELETE FROM bustime_gvote                     WHERE user_id IN (select id from ids))

-- Payment, on_delete=models.SET_NULL
,Payment       AS (UPDATE bustime_payment     SET us_id   = NULL WHERE us_id   IN (select id from ids))

-- Mapping, on_delete=models.SET_NULL
,Mapping       AS (UPDATE bustime_mapping     SET last_changed_by_id = NULL WHERE last_changed_by_id IN (select id from ids))

-- Plan, on_delete=models.SET_NULL
,Plan          AS (UPDATE bustime_plan        SET last_changed_by_id = NULL WHERE last_changed_by_id IN (select id from ids))

-- Like, on_delete=models.SET_NULL
,"Like"        AS (UPDATE bustime_like        SET us_id   = NULL WHERE us_id   IN (select id from ids))

-- Chat, on_delete=models.SET_NULL
,Chat          AS (UPDATE bustime_chat        SET us_id   = NULL WHERE us_id   IN (select id from ids))

-- Diff, on_delete=models.SET_NULL
,Diff          AS (UPDATE bustime_diff        SET us_id   = NULL WHERE us_id   IN (select id from ids))

-- UserSettings
,UserSettings  AS (DELETE FROM bustime_usersettings              WHERE id      IN (select id from ids))

-- это обязательно
SELECT true;
