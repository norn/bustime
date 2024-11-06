DELETE
--SELECT session_key, last_login
FROM django_session
WHERE session_key IN (
    -- выбираем строки с last_login более 90 дней назад (не логинился 3 месяца)
    SELECT session_key
    FROM (
    	SELECT
    		session_key, session_data,
    		-- вырезаем регуляркой дату last_login и преобразуем в дату
    		TO_DATE(SUBSTRING(session_data, '"last_login":"([0-9-]*)"'), 'YYYY-MM-DD') AS last_login
    	FROM (
    		SELECT
    			session_key,
    			-- декодируем base64
    			convert_from(decode(session_data, 'base64'), 'UTF8') as session_data
    		FROM (
    			-- session_data это base64
    			-- если длинна поля не кратна 4, надо дополнить его = до кратной
    			-- {"last_login":"2020-08-04"} длинна закодированного base64 значения минимум 21 символ
    			-- если длинна поля меньше 21 (точно нет last_login), обнуляем
    			SELECT
    				session_key,
    				case
    				WHEN LENGTH(session_data) < 21 THEN null
    				WHEN RIGHT(session_data, 1) <> '=' and LENGTH(session_data) % 4 <> 0 THEN session_data || repeat('=', (4 * ceil(LENGTH(session_data)::FLOAT / 4)::integer) - LENGTH(session_data))
    				ELSE session_data
    				END AS session_data
    			FROM (
    				-- если в поле session_data есть : берём левую часть до : иначе всё
    				SELECT
    					session_key,
    					SPLIT_PART(session_data, ':', 1) AS session_data
    				FROM django_session
    				-- удалить после отладки:
    				--ORDER BY session_key
    				--LIMIT 10
    			) a
                -- так как пока решение для zlib.decompress строк postgresql не нашел, пропустим сжатые строки
    			WHERE LEFT(session_data, 1) <> '.'
    		) b
    	) c
    ) d
    WHERE last_login is null OR CURRENT_DATE - last_login > 90
)
